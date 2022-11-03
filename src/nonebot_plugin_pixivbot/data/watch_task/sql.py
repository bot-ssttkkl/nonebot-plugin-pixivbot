from typing import TypeVar, Optional, AsyncIterable, Collection

from sqlalchemy import Column, Integer, Enum as SqlEnum, JSON, String, select, DateTime, UniqueConstraint, update, Index
from sqlalchemy.dialects.sqlite import insert

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.seq import SeqRepo
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.process_subscriber import process_subscriber
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.require(SqlDataSource).registry.mapped
class WatchTaskOrm:
    __tablename__ = "watch_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscriber = Column(JSON, nullable=False)
    code = Column(Integer, nullable=False)
    type = Column(SqlEnum(WatchType), nullable=False)
    kwargs = Column(JSON, nullable=False, default=dict)
    adapter = Column(String, nullable=False)
    checkpoint = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("watch_task_adapter_idx", "adapter"),
        Index("watch_task_subscriber_code_idx", "subscriber", "code"),
        UniqueConstraint("subscriber", "type", "kwargs", sqlite_on_conflict='IGNORE'),
    )


@context.inject
@context.register_singleton()
class SqlWatchTaskRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)
    seq_repo: SeqRepo = Inject(SeqRepo)

    async def get_by_subscriber(self, subscriber: ID) -> AsyncIterable[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (
            select(WatchTaskOrm)
            .where(WatchTaskOrm.subscriber == subscriber.dict())
        )
        async for x in await session.stream_scalars(stmt):
            yield WatchTask.from_orm(x)

    async def get_by_adapter(self, adapter: str) -> AsyncIterable[WatchTask]:
        session = self.data_source.session()
        stmt = (
            select(WatchTaskOrm)
            .where(WatchTaskOrm.adapter == adapter)
        )
        async for x in await session.stream_scalars(stmt):
            yield WatchTask.from_orm(x)

    async def get_by_code(self, subscriber: ID, code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(WatchTaskOrm)
                .where(WatchTask.subscriber == subscriber.dict(),
                       WatchTask.code == code))
        result = (await session.execute(stmt)).scalar_one_or_none()
        return result

    async def insert(self, task: WatchTask) -> bool:
        task.subscriber = process_subscriber(task.subscriber)

        session = self.data_source.session()
        stmt = (insert(WatchTaskOrm)
                .values(subscriber=task.subscriber.dict(),
                        code=task.code,
                        type=task.type,
                        kwargs=task.kwargs,
                        adapter=task.subscriber.adapter,
                        checkpoint=task.checkpoint))
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount == 1:
            task.code = await self.seq_repo.inc_and_get(f'watch_task {task.subscriber}')

            task_orm = await session.get(WatchTaskOrm, result.inserted_primary_key[0])
            task_orm.code = task.code
            await session.commit()

            return True
        else:
            return False

    async def update(self, task: WatchTask) -> bool:
        task.subscriber = process_subscriber(task.subscriber)

        session = self.data_source.session()
        stmt = (update(WatchTaskOrm)
                .values(type=task.type,
                        kwargs=task.kwargs,
                        adapter=task.subscriber.adapter,
                        checkpoint=task.checkpoint)
                .where(WatchTaskOrm.subscriber == task.subscriber.dict(),
                       WatchTaskOrm.code == task.code))
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount == 1

    async def delete_one(self, subscriber: ID, code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(WatchTaskOrm)
                .where(WatchTaskOrm.subscriber == subscriber.dict(),
                       WatchTaskOrm.code == code)
                .limit(1))
        task = (await session.execute(stmt)).scalar_one_or_none()

        if task is None:
            return task

        await session.delete(task)
        await session.commit()
        return WatchTask.from_orm(task)

    async def delete_many_by_subscriber(self, subscriber: ID) -> Collection[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(WatchTaskOrm)
                .where(WatchTaskOrm.subscriber == subscriber.dict()))
        tasks = (await session.execute(stmt)).scalars().all()

        for t in tasks:
            await session.delete(t)

        await session.commit()
        return tasks


__all__ = ("SqlWatchTaskRepo",)

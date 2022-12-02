from typing import Optional, AsyncIterable, Collection

from pytz import utc
from sqlalchemy import Column, Integer, Enum as SqlEnum, String, select, UniqueConstraint, update, Index

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.process_subscriber import process_subscriber
from nonebot_plugin_pixivbot.data.utils.shortuuid import gen_code
from nonebot_plugin_pixivbot.data.utils.sql import insert, JSON, UTCDateTime
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask, T_UID, T_GID


@context.require(SqlDataSource).registry.mapped
class WatchTaskOrm:
    __tablename__ = "watch_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscriber = Column(JSON, nullable=False)
    code = Column(String, nullable=False)
    type = Column(SqlEnum(WatchType), nullable=False)
    kwargs = Column(JSON, nullable=False, default=dict)
    adapter = Column(String, nullable=False)
    checkpoint = Column(UTCDateTime, nullable=False)

    __table_args__ = (
        Index("ix_watch_task_adapter", "adapter"),
        UniqueConstraint("subscriber", "code"),
        UniqueConstraint("subscriber", "type", "kwargs"),
    )


@context.inject
@context.register_singleton()
class SqlWatchTaskRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (
            select(WatchTaskOrm)
            .where(WatchTaskOrm.subscriber == subscriber.dict())
        )
        async for x in await session.stream_scalars(stmt):
            x.checkpoint = x.checkpoint.replace(tzinfo=utc)
            yield WatchTask.from_orm(x)

    async def get_by_adapter(self, adapter: str) -> AsyncIterable[WatchTask]:
        session = self.data_source.session()
        stmt = (
            select(WatchTaskOrm)
            .where(WatchTaskOrm.adapter == adapter)
        )
        async for x in await session.stream_scalars(stmt):
            x.checkpoint = x.checkpoint.replace(tzinfo=utc)
            yield WatchTask.from_orm(x)

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(WatchTaskOrm)
                .where(WatchTaskOrm.subscriber == subscriber.dict(),
                       WatchTaskOrm.code == code))
        result = (await session.execute(stmt)).scalar_one_or_none()
        result.checkpoint = result.checkpoint.replace(tzinfo=utc)
        return WatchTask.from_orm(result)

    async def insert(self, task: WatchTask) -> bool:
        task.subscriber = process_subscriber(task.subscriber)
        task.code = gen_code()

        session = self.data_source.session()
        stmt = (insert(WatchTaskOrm)
                .values(subscriber=task.subscriber.dict(),
                        code=task.code,
                        type=task.type,
                        kwargs=task.kwargs,
                        adapter=task.subscriber.adapter,
                        checkpoint=task.checkpoint))
        stmt.on_conflict_do_nothing(index_elements=[WatchTaskOrm.type, WatchTaskOrm.kwargs])
        result = await session.execute(stmt)
        await session.commit()

        return result.rowcount == 1

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

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: int) -> Optional[WatchTask]:
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

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[WatchTask]:
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

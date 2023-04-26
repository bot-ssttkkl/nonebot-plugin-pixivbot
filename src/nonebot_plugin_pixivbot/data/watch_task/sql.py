from datetime import datetime
from typing import Optional, AsyncIterable, Collection

from pytz import utc
from sqlalchemy import select, UniqueConstraint, update
from sqlalchemy.orm import mapped_column, Mapped

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask, T_UID, T_GID, UserIdentifier
from .base import WatchTaskRepo
from ..interval_task_repo import process_subscriber
from ..source.sql import SqlDataSource
from ..utils.shortuuid import gen_code
from ..utils.sql import insert, JSON, UTCDateTime


@SqlDataSource.registry.mapped
class WatchTaskOrm:
    __tablename__ = "watch_task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscriber: Mapped[dict] = mapped_column(JSON)
    code: Mapped[str]
    type: Mapped[WatchType]
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    bot: Mapped[str]
    checkpoint: Mapped[datetime] = mapped_column(UTCDateTime)

    __table_args__ = (
        UniqueConstraint("bot", "subscriber", "code"),
        UniqueConstraint("bot", "subscriber", "type", "kwargs"),
    )


def _to_model(item: WatchTaskOrm) -> WatchTask:
    adapter, bot_id = item.bot.split(':')
    return WatchTask(subscriber=PostIdentifier(**item.subscriber),
                     code=item.code,
                     type=item.type,
                     kwargs=item.kwargs,
                     bot=UserIdentifier(adapter, bot_id),
                     checkpoint=item.checkpoint)


data_source = context.require(SqlDataSource)


@context.register_singleton()
class SqlWatchTaskRepo(WatchTaskRepo):

    async def get_by_subscriber(self, bot: UserIdentifier[T_UID],
                                subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[WatchTask[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (
                select(WatchTaskOrm)
                .where(WatchTaskOrm.bot == str(bot),
                       WatchTaskOrm.subscriber == subscriber.dict())
            )
            async for x in await session.stream_scalars(stmt):
                x.checkpoint = x.checkpoint.replace(tzinfo=utc)
                yield _to_model(x)

    async def get_by_bot(self, bot: UserIdentifier[T_UID]) -> AsyncIterable[WatchTask[T_UID, T_GID]]:
        async with data_source.start_session() as session:
            stmt = (
                select(WatchTaskOrm)
                .where(WatchTaskOrm.bot == str(bot))
            )
            async for x in await session.stream_scalars(stmt):
                x.checkpoint = x.checkpoint.replace(tzinfo=utc)
                yield _to_model(x)

    async def get_by_code(self, bot: UserIdentifier[T_UID],
                          subscriber: PostIdentifier[T_UID, T_GID],
                          code: int) -> Optional[WatchTask[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot == str(bot),
                           WatchTaskOrm.subscriber == subscriber.dict(),
                           WatchTaskOrm.code == code))
            result = (await session.execute(stmt)).scalar_one_or_none()
            result.checkpoint = result.checkpoint.replace(tzinfo=utc)
            return _to_model(result)

    async def insert(self, item: WatchTask[T_UID, T_GID]) -> bool:
        item.subscriber = process_subscriber(item.subscriber)
        item.code = gen_code()

        async with data_source.start_session() as session:
            stmt = (insert(WatchTaskOrm)
                    .values(subscriber=item.subscriber.dict(),
                            code=item.code,
                            type=item.type,
                            kwargs=item.kwargs,
                            bot=str(item.bot),
                            checkpoint=item.checkpoint))
            stmt = stmt.on_conflict_do_nothing()
            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount == 1

    async def update(self, item: WatchTask[T_UID, T_GID]) -> bool:
        item.subscriber = process_subscriber(item.subscriber)

        async with data_source.start_session() as session:
            stmt = (update(WatchTaskOrm)
                    .values(type=item.type,
                            kwargs=item.kwargs,
                            bot=str(item.bot),
                            checkpoint=item.checkpoint)
                    .where(WatchTaskOrm.subscriber == item.subscriber.dict(),
                           WatchTaskOrm.code == item.code))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount == 1

    async def delete_one(self, bot: UserIdentifier[T_UID],
                         subscriber: PostIdentifier[T_UID, T_GID],
                         code: int) -> Optional[WatchTask[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot == str(bot),
                           WatchTaskOrm.subscriber == subscriber.dict(),
                           WatchTaskOrm.code == code)
                    .limit(1))
            task = (await session.execute(stmt)).scalar_one_or_none()

            if task is None:
                return task

            await session.delete(task)
            await session.commit()
            return _to_model(task)

    async def delete_many_by_subscriber(self, bot: UserIdentifier[T_UID],
                                        subscriber: PostIdentifier[T_UID, T_GID]) \
            -> Collection[WatchTask[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot == str(bot),
                           WatchTaskOrm.subscriber == subscriber.dict()))
            tasks = (await session.execute(stmt)).scalars().all()

            for t in tasks:
                await session.delete(t)

            await session.commit()
            return [_to_model(x) for x in tasks]


__all__ = ("SqlWatchTaskRepo",)

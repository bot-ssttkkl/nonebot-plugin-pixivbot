from typing import Optional, AsyncIterable, Collection

import tzlocal
from sqlalchemy import select, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, ScheduleType, T_UID, T_GID, UserIdentifier
from .base import SubscriptionRepo
from ..interval_task_repo import process_subscriber
from ..source.sql import SqlDataSource
from ..utils.shortuuid import gen_code
from ..utils.sql import insert, JSON


@SqlDataSource.registry.mapped
class SubscriptionOrm:
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscriber: Mapped[dict] = mapped_column(JSON)
    code: Mapped[str]
    type: Mapped[ScheduleType]
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    bot: Mapped[str]
    schedule: Mapped[dict] = mapped_column(JSON)
    tz: Mapped[str] = mapped_column(default=tzlocal.get_localzone_name)

    __table_args__ = (
        UniqueConstraint("bot", "subscriber", "code"),
    )


def _to_model(item: SubscriptionOrm) -> Subscription:
    adapter, bot_id = item.bot.split(':')
    return Subscription(subscriber=PostIdentifier(**item.subscriber),
                        code=item.code,
                        type=item.type,
                        kwargs=item.kwargs,
                        bot=UserIdentifier(adapter, bot_id),
                        schedule=item.schedule,
                        tz=item.tz)


data_source = context.require(SqlDataSource)


@context.register_singleton()
class SqlSubscriptionRepo(SubscriptionRepo):

    async def get_by_subscriber(self, bot: UserIdentifier[T_UID],
                                subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[Subscription]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.bot == str(bot),
                       SubscriptionOrm.subscriber == subscriber.dict())
            )
            async for x in await session.stream_scalars(stmt):
                yield _to_model(x)

    async def get_by_bot(self, bot: UserIdentifier[T_UID]) -> AsyncIterable[Subscription]:
        async with data_source.start_session() as session:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.bot == str(bot))
            )
            async for x in await session.stream_scalars(stmt):
                yield _to_model(x)

    async def get_by_code(self, bot: UserIdentifier[T_UID],
                          subscriber: PostIdentifier[T_UID, T_GID],
                          code: str) -> Optional[Subscription]:
        async with data_source.start_session() as session:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.bot == str(bot),
                       SubscriptionOrm.subscriber == subscriber.dict(),
                       SubscriptionOrm.code == code)
            )
            x = (await session.execute(stmt)).scalar_one_or_none()
            if x is not None:
                return _to_model(x)
            else:
                return None

    async def insert(self, item: Subscription[T_UID, T_GID]) -> bool:
        item.subscriber = process_subscriber(item.subscriber)
        item.code = gen_code()

        async with data_source.start_session() as session:
            stmt = (insert(SubscriptionOrm)
                    .values(subscriber=item.subscriber.dict(),
                            code=item.code,
                            type=item.type,
                            kwargs=item.kwargs,
                            bot=str(item.bot),
                            schedule=item.schedule,
                            tz=item.tz))
            await session.execute(stmt)
            await session.commit()
        return True

    async def delete_one(self, bot: UserIdentifier[T_UID],
                         subscriber: PostIdentifier[T_UID, T_GID],
                         code: int) -> Optional[Subscription]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (select(SubscriptionOrm)
                    .where(SubscriptionOrm.bot == str(bot),
                           SubscriptionOrm.subscriber == subscriber.dict(),
                           SubscriptionOrm.code == code)
                    .limit(1))
            sub = (await session.execute(stmt)).scalar_one_or_none()

            if sub is None:
                return sub

            await session.delete(sub)
            await session.commit()
            return _to_model(sub)

    async def delete_many_by_subscriber(self, bot: UserIdentifier[T_UID],
                                        subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[Subscription]:
        subscriber = process_subscriber(subscriber)

        async with data_source.start_session() as session:
            stmt = (select(SubscriptionOrm)
                    .where(SubscriptionOrm.bot == str(bot),
                           SubscriptionOrm.subscriber == subscriber.dict()))
            subs = (await session.execute(stmt)).scalars().all()

            for t in subs:
                await session.delete(t)

            await session.commit()
            return [_to_model(x) for x in subs]


__all__ = ("SqlSubscriptionRepo",)

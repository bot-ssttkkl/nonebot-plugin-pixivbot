from typing import Optional, AsyncIterable, Collection

import tzlocal
from sqlalchemy import Column, Integer, Enum as SqlEnum, String, select, Index, UniqueConstraint

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.process_subscriber import process_subscriber
from nonebot_plugin_pixivbot.data.utils.shortuuid import gen_code
from nonebot_plugin_pixivbot.data.utils.sql import insert, JSON
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, ScheduleType, T_UID, T_GID


@context.require(SqlDataSource).registry.mapped
class SubscriptionOrm:
    __tablename__ = "subscription"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscriber = Column(JSON, nullable=False)
    code = Column(String, nullable=False)
    type = Column(SqlEnum(ScheduleType), nullable=False)
    kwargs = Column(JSON, nullable=False, default=dict)
    adapter = Column(String, nullable=False)
    schedule = Column(JSON, nullable=False)
    tz = Column(String, nullable=False, default=tzlocal.get_localzone_name)

    __table_args__ = (
        Index("ix_subscription_adapter", "adapter"),
        UniqueConstraint("subscriber", "code"),
    )


@context.inject
@context.register_singleton()
class SqlSubscriptionRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[Subscription]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (
            select(SubscriptionOrm)
            .where(SubscriptionOrm.subscriber == subscriber.dict())
        )
        async for x in await session.stream_scalars(stmt):
            yield Subscription.from_orm(x)

    async def get_by_adapter(self, adapter: str) -> AsyncIterable[Subscription]:
        session = self.data_source.session()
        stmt = (
            select(SubscriptionOrm)
            .where(SubscriptionOrm.adapter == adapter)
        )
        async for x in await session.stream_scalars(stmt):
            yield Subscription.from_orm(x)

    async def insert(self, subscription: Subscription):
        subscription.subscriber = process_subscriber(subscription.subscriber)
        subscription.code = gen_code()

        session = self.data_source.session()
        stmt = (insert(SubscriptionOrm)
                .values(subscriber=subscription.subscriber.dict(),
                        code=subscription.code,
                        type=subscription.type,
                        kwargs=subscription.kwargs,
                        adapter=subscription.subscriber.adapter,
                        schedule=subscription.schedule,
                        tz=subscription.tz))
        await session.execute(stmt)
        await session.commit()

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: int) -> Optional[Subscription]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(SubscriptionOrm)
                .where(SubscriptionOrm.subscriber == subscriber.dict(),
                       SubscriptionOrm.code == code)
                .limit(1))
        sub = (await session.execute(stmt)).scalar_one_or_none()

        if sub is None:
            return sub

        await session.delete(sub)
        await session.commit()
        return Subscription.from_orm(sub)

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[Subscription]:
        subscriber = process_subscriber(subscriber)

        session = self.data_source.session()
        stmt = (select(SubscriptionOrm)
                .where(SubscriptionOrm.subscriber == subscriber.dict()))
        subs = (await session.execute(stmt)).scalars().all()

        for t in subs:
            await session.delete(t)

        await session.commit()
        return subs


__all__ = ("SqlSubscriptionRepo",)

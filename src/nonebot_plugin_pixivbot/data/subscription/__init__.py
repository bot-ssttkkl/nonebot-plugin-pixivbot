from typing import Optional, Protocol, AsyncIterable, Collection

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, T_UID, T_GID
from ...enums import DataSourceType


class SubscriptionRepo(Protocol):
    def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[Subscription]:
        ...

    def get_by_adapter(self, adapter: str) -> AsyncIterable[Subscription]:
        ...

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[Subscription]:
        ...

    async def insert(self, subscription: Subscription):
        ...

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[Subscription]:
        ...

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[Subscription]:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoSubscriptionRepo

    context.bind(SubscriptionRepo, MongoSubscriptionRepo)
else:
    from .sql import SqlSubscriptionRepo

    context.bind(SubscriptionRepo, SqlSubscriptionRepo)

__all__ = ("SubscriptionRepo",)

from typing import TypeVar, Optional, Protocol, AsyncIterable, Collection

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier
from ...enums import DataSourceType

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class SubscriptionRepo(Protocol):
    def get_by_subscriber(self, subscriber: ID) -> AsyncIterable[Subscription]:
        ...

    def get_by_adapter(self, adapter: str) -> AsyncIterable[Subscription]:
        ...

    async def get_by_code(self, subscriber: ID, code: int) -> Optional[Subscription]:
        ...

    async def insert(self, subscription: Subscription):
        ...

    async def delete_one(self, subscriber: ID, code: int) -> Optional[Subscription]:
        ...

    async def delete_many_by_subscriber(self, subscriber: ID) -> Collection[Subscription]:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoSubscriptionRepo

    context.bind(SubscriptionRepo, MongoSubscriptionRepo)
else:
    from .sql import SqlSubscriptionRepo

    context.bind(SubscriptionRepo, SqlSubscriptionRepo)

__all__ = ("SubscriptionRepo",)

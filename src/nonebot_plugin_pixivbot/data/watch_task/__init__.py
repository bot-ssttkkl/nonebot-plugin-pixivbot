from typing import TypeVar, Optional, Protocol, AsyncIterable, Collection

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchTask
from ...enums import DataSourceType

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class WatchTaskRepo(Protocol):
    def get_by_subscriber(self, subscriber: ID) -> AsyncIterable[WatchTask]:
        ...

    def get_by_adapter(self, adapter: str) -> AsyncIterable[WatchTask]:
        ...

    async def get_by_code(self, subscriber: ID, code: int) -> Optional[WatchTask]:
        ...

    async def insert(self, task: WatchTask) -> bool:
        ...

    async def update(self, task: WatchTask) -> bool:
        ...

    async def delete_one(self, subscriber: ID, code: int) -> Optional[WatchTask]:
        ...

    async def delete_many_by_subscriber(self, subscriber: ID) -> Collection[WatchTask]:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoWatchTaskRepo

    context.bind(WatchTaskRepo, MongoWatchTaskRepo)
else:
    from .sql import SqlWatchTaskRepo

    context.bind(WatchTaskRepo, SqlWatchTaskRepo)

__all__ = ("WatchTaskRepo",)

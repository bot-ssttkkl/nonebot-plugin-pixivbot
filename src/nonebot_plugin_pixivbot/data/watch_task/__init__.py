from typing import Optional, Protocol, AsyncIterable, Collection

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchTask, T_UID, T_GID


class WatchTaskRepo(Protocol):
    def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[WatchTask]:
        ...

    def get_by_adapter(self, adapter: str) -> AsyncIterable[WatchTask]:
        ...

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[WatchTask]:
        ...

    async def insert(self, task: WatchTask) -> bool:
        ...

    async def update(self, task: WatchTask) -> bool:
        ...

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[WatchTask]:
        ...

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[WatchTask]:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoWatchTaskRepo

    context.bind(WatchTaskRepo, MongoWatchTaskRepo)
else:
    from .sql import SqlWatchTaskRepo

    context.bind(WatchTaskRepo, SqlWatchTaskRepo)

__all__ = ("WatchTaskRepo",)

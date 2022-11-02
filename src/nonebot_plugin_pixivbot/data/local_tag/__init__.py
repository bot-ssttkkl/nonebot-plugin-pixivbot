from typing import Optional, Protocol, Collection

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import Tag, Illust
from ...enums import DataSourceType


class LocalTagRepo(Protocol):
    async def find_by_name(self, name: str) -> Optional[Tag]:
        ...

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        ...

    async def update_one(self, tag: Tag):
        ...

    async def update_many(self, tags: Collection[Tag]):
        ...

    async def update_from_illusts(self, illusts: Collection[Illust]):
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoLocalTagRepo

    context.bind(LocalTagRepo, MongoLocalTagRepo)
else:
    from .sql import SqlLocalTagRepo

    context.bind(LocalTagRepo, SqlLocalTagRepo)

__all__ = ("LocalTagRepo",)

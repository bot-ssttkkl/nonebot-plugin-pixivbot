from typing import Optional, TypeVar, Protocol

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.model import PixivBinding

UID = TypeVar("UID")


class PixivBindingRepo(Protocol):
    async def get(self, adapter: str, user_id: UID) -> Optional[PixivBinding]:
        ...

    async def update(self, binding: PixivBinding):
        ...

    async def remove(self, adapter: str, user_id: UID) -> bool:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivBindingRepo

    context.bind(PixivBindingRepo, MongoPixivBindingRepo)
else:
    from .sql import SqlPixivBindingRepo

    context.bind(PixivBindingRepo, SqlPixivBindingRepo)

__all__ = ("PixivBindingRepo",)

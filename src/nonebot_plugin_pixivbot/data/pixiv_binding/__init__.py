from typing import Optional, Protocol

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.model import PixivBinding, T_UID


class PixivBindingRepo(Protocol):
    async def get(self, adapter: str, user_id: T_UID) -> Optional[PixivBinding]:
        ...

    async def update(self, binding: PixivBinding):
        ...

    async def remove(self, adapter: str, user_id: T_UID) -> bool:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivBindingRepo

    context.bind(PixivBindingRepo, MongoPixivBindingRepo)
else:
    from .sql import SqlPixivBindingRepo

    context.bind(PixivBindingRepo, SqlPixivBindingRepo)

__all__ = ("PixivBindingRepo",)

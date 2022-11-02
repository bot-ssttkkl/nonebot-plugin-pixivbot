from typing import Protocol

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType


class SeqRepo(Protocol):
    async def inc_and_get(self, key: str) -> int:
        ...

    async def get_and_inc(self, key: str) -> int:
        ...

    async def get(self, key: str) -> int:
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoSeqRepo

    context.bind(SeqRepo, MongoSeqRepo)
else:
    from .sql import SqlSeqRepo

    context.bind(SeqRepo, SqlSeqRepo)

__all__ = ("SeqRepo",)

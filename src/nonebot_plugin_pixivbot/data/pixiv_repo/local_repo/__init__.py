from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
from .base import LocalPixivRepo

conf = context.require(Config)
if not conf.pixiv_use_local_cache:
    from .dummy import DummyPixivRepo

    context.bind(LocalPixivRepo, DummyPixivRepo)
    logger.info("local cache: disabled")
elif conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivRepo

    context.bind(LocalPixivRepo, MongoPixivRepo)
    logger.info("local cache: enabled (mongodb)")
else:
    from .sql import SqlPixivRepo

    context.bind(LocalPixivRepo, SqlPixivRepo)
    logger.info(f"local cache: enabled ({conf.pixiv_sql_dialect})")

__all__ = ("LocalPixivRepo",)

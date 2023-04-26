from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
from .base import WatchTaskRepo

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoWatchTaskRepo

    context.bind(WatchTaskRepo, MongoWatchTaskRepo)
else:
    from .sql import SqlWatchTaskRepo

    context.bind(WatchTaskRepo, SqlWatchTaskRepo)

__all__ = ("WatchTaskRepo",)

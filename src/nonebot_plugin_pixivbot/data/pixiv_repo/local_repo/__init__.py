from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
from .base import LocalPixivRepo

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivRepo

    context.bind(LocalPixivRepo, MongoPixivRepo)
else:
    from .sql import SqlPixivRepo

    context.bind(LocalPixivRepo, SqlPixivRepo)

__all__ = ("LocalPixivRepo",)

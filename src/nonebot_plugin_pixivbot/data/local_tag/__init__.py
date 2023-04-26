from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from .base import LocalTagRepo
from ...enums import DataSourceType

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoLocalTagRepo

    context.bind(LocalTagRepo, MongoLocalTagRepo)
else:
    from .sql import SqlLocalTagRepo

    context.bind(LocalTagRepo, SqlLocalTagRepo)

__all__ = ("LocalTagRepo",)

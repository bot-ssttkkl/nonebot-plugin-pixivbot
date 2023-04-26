from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
from .base import PixivBindingRepo

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivBindingRepo

    context.bind(PixivBindingRepo, MongoPixivBindingRepo)
else:
    from .sql import SqlPixivBindingRepo

    context.bind(PixivBindingRepo, SqlPixivBindingRepo)

__all__ = ("PixivBindingRepo",)

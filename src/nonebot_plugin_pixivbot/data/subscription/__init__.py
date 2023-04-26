from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from .base import SubscriptionRepo
from ...enums import DataSourceType

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoSubscriptionRepo

    context.bind(SubscriptionRepo, MongoSubscriptionRepo)
else:
    from .sql import SqlSubscriptionRepo

    context.bind(SubscriptionRepo, SqlSubscriptionRepo)

__all__ = ("SubscriptionRepo",)

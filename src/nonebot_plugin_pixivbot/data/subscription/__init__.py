from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import Subscription
from ..interval_task_repo import IntervalTaskRepo
from ...enums import DataSourceType


class SubscriptionRepo(IntervalTaskRepo[Subscription]):
    ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoSubscriptionRepo

    context.bind(SubscriptionRepo, MongoSubscriptionRepo)
else:
    from .sql import SqlSubscriptionRepo

    context.bind(SubscriptionRepo, SqlSubscriptionRepo)

__all__ = ("SubscriptionRepo",)

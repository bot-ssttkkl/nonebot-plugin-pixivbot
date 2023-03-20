from nonebot_plugin_pixivbot.handler.common import RandomIllustHandler
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


class SubscriptionRandomIllustHandler(SubscriptionHandler, RandomIllustHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.random_illust

    @classmethod
    def enabled(cls) -> bool:
        return True

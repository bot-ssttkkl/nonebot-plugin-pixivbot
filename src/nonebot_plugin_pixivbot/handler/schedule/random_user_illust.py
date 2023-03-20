from nonebot_plugin_pixivbot.handler.common import RandomUserIllustHandler
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


class SubscriptionRandomUserIllustHandler(SubscriptionHandler, RandomUserIllustHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.random_user_illust

    @classmethod
    def enabled(cls) -> bool:
        return True

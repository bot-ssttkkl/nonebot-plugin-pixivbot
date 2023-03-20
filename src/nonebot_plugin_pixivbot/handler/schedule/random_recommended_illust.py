from nonebot_plugin_pixivbot.handler.common import RandomRecommendedIllustHandler
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


class SubscriptionRandomRecommendedIllustHandler(SubscriptionHandler, RandomRecommendedIllustHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.random_recommended_illust

    @classmethod
    def enabled(cls) -> bool:
        return True

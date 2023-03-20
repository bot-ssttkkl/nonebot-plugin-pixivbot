from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


class SubscriptionRandomBookmarkHandler(SubscriptionHandler, RandomBookmarkHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.random_bookmark

    @classmethod
    def enabled(cls) -> bool:
        return True

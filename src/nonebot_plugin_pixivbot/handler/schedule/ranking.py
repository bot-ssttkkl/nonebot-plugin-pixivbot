from nonebot_plugin_pixivbot.handler.common import RankingHandler
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


class SubscriptionRankingHandler(SubscriptionHandler, RankingHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.ranking

    @classmethod
    def enabled(cls) -> bool:
        return True

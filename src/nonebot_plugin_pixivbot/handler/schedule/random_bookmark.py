from nonebot_plugin_pixivbot.handler.base import Handler
from nonebot_plugin_pixivbot.handler.pkg_context import context
from nonebot_plugin_pixivbot.handler.schedule.base import SubscriptionHandler
from nonebot_plugin_pixivbot.model import ScheduleType


@context.root.register_eager_singleton()
class SubscriptionRandomBookmarkHandler(SubscriptionHandler):
    @classmethod
    def type(cls) -> str:
        return ScheduleType.random_bookmark

    def enabled(self) -> bool:
        return True

    @property
    def delegation(self) -> Handler:
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler
        return context.require(RandomBookmarkHandler)

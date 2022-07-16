from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import MoreHandler
from nonebot_plugin_pixivbot.query.query import Query
from nonebot_plugin_pixivbot.query.utils import get_count


@context.register_singleton()
class MoreQuery(Query):
    def __init__(self):
        super().__init__()
        self.handler = context.require(MoreHandler)

    @lazy
    def matcher(self):
        return on_regex("^还要((.*)张)?$", priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(count=get_count(state, 1), post_dest=post_dest)

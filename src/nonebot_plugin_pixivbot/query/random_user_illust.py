from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import RandomUserIllustHandler
from nonebot_plugin_pixivbot.query.query import Query
from nonebot_plugin_pixivbot.query.utils import get_count


@context.register_singleton()
class RandomUserIllustQuery(Query):
    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张(.+)老师的图$", priority=4, block=True)

    def __init__(self):
        super().__init__()
        self.handler = context.require(RandomUserIllustHandler)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        user = state["_matched_groups"][1]

        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(user, count=get_count(state), post_dest=post_dest)

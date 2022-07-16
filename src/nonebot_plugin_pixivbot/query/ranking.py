from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import RankingHandler
from nonebot_plugin_pixivbot.query.query import Query


@context.register_singleton()
class RankingQuery(Query):
    @lazy
    def matcher(self):
        return on_regex(r"^看看(.*)?榜\s*(.*)?$", priority=4, block=True)

    def __init__(self):
        super().__init__()
        self.handler = context.require(RankingHandler)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        if "_matched_groups" in state:
            mode = state["_matched_groups"][0]
            num = state["_matched_groups"][1]
        else:
            mode = None
            num = None

        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(mode, num, post_dest=post_dest)

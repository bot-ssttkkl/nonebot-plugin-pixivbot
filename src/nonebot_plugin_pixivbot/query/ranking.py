from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common import RankingHandler
from .query import Query, register_query
from .utils import get_common_query_rule, get_post_dest


@context.inject
@register_query(context)
class RankingQuery(Query):
    handler: RankingHandler

    @lazy
    def matcher(self):
        return on_regex(r"^看看(.*)?榜\s*(.*)?$", rule=get_common_query_rule(), priority=4, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        if "_matched_groups" in state:
            mode = state["_matched_groups"][0]
            num = state["_matched_groups"][1]
        else:
            mode = None
            num = None

        await self.handler.handle(mode, num, post_dest=get_post_dest(bot, event))

from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common import MoreHandler
from .query import Query, register_query
from .utils import get_count, get_common_query_rule, get_post_dest


@context.inject
@register_query(context)
class MoreQuery(Query):
    handler: MoreHandler

    @lazy
    def matcher(self):
        return on_regex("^还要((.*)张)?$", rule=get_common_query_rule(), priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        await self.handler.handle(count=get_count(state, 1), post_dest=get_post_dest(bot, event))

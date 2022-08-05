from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common import RandomRelatedIllustHandler
from .query import Query, register_query
from .utils import get_common_query_rule, get_post_dest


@context.inject
@register_query(context)
class RandomRelatedIllustQuery(Query):
    handler: RandomRelatedIllustHandler

    @lazy
    def matcher(self):
        return on_regex("^不够色$", rule=get_common_query_rule(), priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        await self.handler.handle(post_dest=get_post_dest(bot, event))

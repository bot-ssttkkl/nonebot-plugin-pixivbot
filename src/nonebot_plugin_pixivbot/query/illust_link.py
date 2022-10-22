from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common import IllustHandler
from .query import Query, register_query
from .utils import get_common_query_rule, get_post_dest


@context.inject
@register_query(context)
class IllustLinkQuery(Query):
    handler: IllustHandler

    @lazy
    def matcher(self):
        return on_regex(r"^(http://|https://)?(www.)?pixiv\.net/artworks/([1-9][0-9]*)/?$",
                        rule=get_common_query_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        illust_id = state["_matched_groups"][2]

        await self.handler.handle(illust_id, post_dest=get_post_dest(bot, event))

from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import RandomRelatedIllustHandler
from nonebot_plugin_pixivbot.query.query import Query
from nonebot_plugin_pixivbot.query.query_manager import QueryManager
from nonebot_plugin_pixivbot.query.utils import get_common_query_rule


@context.require(QueryManager).query
class RandomRelatedIllustQuery(Query):
    def __init__(self):
        super().__init__()
        self.handler = context.require(RandomRelatedIllustHandler)

    @lazy
    def matcher(self):
        return on_regex("^不够色$", rule=get_common_query_rule(), priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(post_dest=post_dest)

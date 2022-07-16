from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import RandomBookmarkHandler
from nonebot_plugin_pixivbot.query.query import Query
from nonebot_plugin_pixivbot.query.query_manager import QueryManager
from nonebot_plugin_pixivbot.query.utils import get_count


@context.require(QueryManager).query
class RandomBookmarkQuery(Query):
    conf = context.require(Config)

    def __init__(self):
        super().__init__()
        self.handler = context.require(RandomBookmarkHandler)

    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张私家车$", priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(count=get_count(state), post_dest=post_dest)

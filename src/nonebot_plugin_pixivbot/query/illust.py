from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler import IllustHandler
from nonebot_plugin_pixivbot.query.query import Query


@context.register_singleton()
class IllustQuery(Query):
    def __init__(self):
        super().__init__()
        self.handler = context.require(IllustHandler)

    @lazy
    def matcher(self):
        return on_regex(r"^看看图\s*([1-9][0-9]*)$", priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        illust_id = state["_matched_groups"][0]

        post_dest = self.post_dest_factory.from_message_event(event)
        await self.handler.handle(illust_id, post_dest=post_dest)

from typing import Dict, Type

from lazy import lazy
from nonebot import on_notice, Bot
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import PokeNotifyEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.base import Handler, DelegationHandler, post_destination, \
    MatcherEntryHandler
from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler, RandomRecommendedIllustHandler, RankingHandler
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot_onebot_v11.config import OnebotV11Config


async def _poke(event: Event) -> bool:
    return isinstance(event, PokeNotifyEvent) and event.is_tome()


@context.root.register_eager_singleton()
class PokeHandler(DelegationHandler, MatcherEntryHandler):
    adapter_conf = context.require(OnebotV11Config)

    query_mapping: Dict[str, Type[Handler]] = {
        "ranking": RankingHandler,
        "random_recommended_illust": RandomRecommendedIllustHandler,
        "random_bookmark": RandomBookmarkHandler
    }

    @classmethod
    def type(cls) -> str:
        return "poke"

    def enabled(self) -> bool:
        return bool(self.adapter_conf.pixiv_poke_action)

    @lazy
    def matcher(self):
        return on_notice(_poke, priority=10, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        await self.handle(post_dest=post_dest)

    @lazy
    def delegation(self):
        query_type = self.query_mapping.get(self.adapter_conf.pixiv_poke_action)
        if query_type:
            return context.require(query_type)
        else:
            raise ValueError(f"invalid config: pixiv_poke_action={self.adapter_conf.pixiv_poke_action}")

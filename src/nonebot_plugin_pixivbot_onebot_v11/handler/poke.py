from typing import Dict, Type

from nonebot import on_notice
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import PokeNotifyEvent
from nonebot.internal.params import Depends

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.base import Handler
from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler, RandomRecommendedIllustHandler, RankingHandler
from nonebot_plugin_pixivbot.protocol_dep.post_dest import post_destination
from nonebot_plugin_pixivbot_onebot_v11.config import OnebotV11Config

adapter_conf = context.require(OnebotV11Config)

handler_type_mapping: Dict[str, Type[Handler]] = {
    "ranking": RankingHandler,
    "random_recommended_illust": RandomRecommendedIllustHandler,
    "random_bookmark": RandomBookmarkHandler
}

handler_type = handler_type_mapping.get(adapter_conf.pixiv_poke_action, None)

if handler_type is not None:
    class PokeHandler(handler_type):
        @classmethod
        def type(cls) -> str:
            return "poke"

        @classmethod
        def enabled(cls) -> bool:
            return handler_type is not None


    async def _poke(event: Event) -> bool:
        return isinstance(event, PokeNotifyEvent) and event.is_tome()


    @on_notice(_poke, priority=10, block=True).handle()
    async def on_match(post_dest=Depends(post_destination)):
        await PokeHandler(post_dest).handle()

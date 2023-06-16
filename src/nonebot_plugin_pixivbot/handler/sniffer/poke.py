from typing import Dict, Type

from nonebot import on_notice, Bot
from nonebot.adapters import Event
from nonebot.internal.params import Depends
from nonebot_plugin_session import extract_session

from ..base import Handler
from ..common import RandomBookmarkHandler, RandomRecommendedIllustHandler, RankingHandler
from ...config import Config
from ...global_context import context

conf = context.require(Config)

handler_type_mapping: Dict[str, Type[Handler]] = {
    "ranking": RankingHandler,
    "random_recommended_illust": RandomRecommendedIllustHandler,
    "random_bookmark": RandomBookmarkHandler
}

handler_type = handler_type_mapping.get(conf.pixiv_poke_action, None)

if handler_type is not None:
    class PokeHandler(handler_type):
        @classmethod
        def type(cls) -> str:
            return "poke"


    def _poke(bot: Bot, event: Event) -> bool:
        if bot.type != "OneBot V11":
            return False

        from nonebot.adapters.onebot.v11 import PokeNotifyEvent
        return isinstance(event, PokeNotifyEvent) and event.is_tome()


    @on_notice(_poke, priority=10, block=True).handle()
    async def on_match(event: Event, session=Depends(extract_session)):
        await PokeHandler(session, event).handle()

# import nonebot
from abc import ABC, abstractmethod

from lazy import lazy
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman import PostDestinationFactory


class Query(ABC):
    @lazy
    def post_dest_factory(self):
        return context.require(PostDestinationFactory)

    @property
    @abstractmethod
    def matcher(self) -> Matcher:
        raise NotImplementedError()

    @abstractmethod
    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        raise NotImplementedError()

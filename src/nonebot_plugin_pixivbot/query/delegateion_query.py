from abc import ABC, abstractmethod

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from .query import Query


class DelegationQuery(Query, ABC):
    @property
    @abstractmethod
    def delegation(self) -> Query:
        raise NotImplementedError()

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        await self.delegation.on_match(bot, event, state, matcher)

from abc import ABC, abstractmethod

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State


class Query(ABC):
    @property
    @abstractmethod
    def matcher(self) -> Matcher:
        raise NotImplementedError()

    @abstractmethod
    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        raise NotImplementedError()

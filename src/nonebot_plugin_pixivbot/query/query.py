from abc import ABC, abstractmethod
from typing import Type

from nonebot import logger
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.context import Context


class Query(ABC):
    @property
    @abstractmethod
    def matcher(self) -> Type[Matcher]:
        raise NotImplementedError()

    @abstractmethod
    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher):
        raise NotImplementedError()


def register_query(context: Context):
    def decorator(cls: Type[Query]):
        if cls in context:
            q = context.require(cls)
        else:
            q = cls()
            context.register(cls, q)

        q.matcher.append_handler(q.on_match)
        logger.trace(f"registered query {cls}")
        return cls

    return decorator

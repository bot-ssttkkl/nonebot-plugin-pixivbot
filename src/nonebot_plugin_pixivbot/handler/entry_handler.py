from abc import ABC, abstractmethod
from typing import TypeVar, Type

from nonebot.adapters import Bot, Event
from nonebot.internal.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.handler import Handler
from .interceptor.default_error_interceptor import DefaultErrorInterceptor
from .interceptor.permission_interceptor import BlacklistInterceptor
from ..protocol_dep.post_dest import PostDestinationFactoryManager, PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


def post_destination(bot: Bot, event: Event):
    return context.require(PostDestinationFactoryManager).from_event(bot, event)


class EntryHandler(Handler, ABC):
    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(DefaultErrorInterceptor))
        self.add_interceptor(context.require(BlacklistInterceptor))

        self.matcher.append_handler(self.on_match)

    @property
    @abstractmethod
    def matcher(self) -> Type[Matcher]:
        raise NotImplementedError()

    @abstractmethod
    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[UID, GID] = Depends(post_destination)):
        raise NotImplementedError()


class DelegationEntryHandler(EntryHandler, ABC):
    @property
    @abstractmethod
    def delegation(self) -> EntryHandler:
        raise NotImplementedError()

    async def handle(self, *args,
                     post_dest: PostDestination[UID, GID],
                     silently: bool = False,
                     disabled_interceptors: bool = False,
                     **kwargs):
        if not self.enabled():
            return

        await self.delegation.handle(*args, post_dest=post_dest, silently=silently,
                                     disabled_interceptors=disabled_interceptors, **kwargs)

    async def actual_handle(self, *args, **kwargs):
        raise RuntimeError("unexpected call here")

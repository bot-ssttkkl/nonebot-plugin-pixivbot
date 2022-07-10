from functools import partial
from mailbox import Message
from typing import Callable, TypeVar, Generic, Type, Optional, Iterable

from nonebot import Bot

from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class CombinedInterceptor(Interceptor[UID, GID, B, M], Generic[UID, GID, B, M]):
    def __init__(self, x: Interceptor[UID, GID, B, M], y: Interceptor[UID, GID, B, M]):
        self.x = x
        self.y = y

    @staticmethod
    def from_iterable(interceptors: Iterable[Interceptor]) -> "Interceptor":
        itcp = None
        for x in interceptors:
            if itcp is None:
                itcp = x
            else:
                itcp = CombinedInterceptor(itcp, x)
        if itcp is None:
            raise ValueError("interceptors has no element")
        return itcp

    def find(self, interceptor_type: Type[Interceptor]) -> Optional[Interceptor]:
        if isinstance(interceptor_type, CombinedInterceptor):
            raise ValueError("you are attempting to find a CombinedInterceptor")
        if isinstance(self.x, interceptor_type):
            return self.x
        elif isinstance(self.y, interceptor_type):
            return self.y
        else:
            result = None
            if isinstance(self.x, CombinedInterceptor):
                result = self.x.find(interceptor_type)
            if not result and isinstance(self.y, CombinedInterceptor):
                result = self.y.find(interceptor_type)
            return result

    async def intercept(self, wrapped_func: Callable,
                        post_dest: PostDestination[UID, GID, B, M],
                        silently: bool,
                        **kwargs):
        await self.x.intercept(
            partial(self.y.intercept, wrapped_func),
            post_dest=post_dest, silently=silently, **kwargs
        )
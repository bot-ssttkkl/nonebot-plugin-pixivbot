from functools import partial
from typing import Callable, Type, Optional, Iterable

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import Interceptor


class CombinedInterceptor(Interceptor):
    def __init__(self, x: Interceptor, y: Interceptor):
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

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        await self.x.intercept(
            partial(self.y.intercept, wrapped_func), *args,
            post_dest=post_dest, silently=silently, **kwargs
        )

from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, TypeVar

from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


class Interceptor(ABC):
    def __call__(self, wrapped: Callable):
        @wraps(wrapped)
        async def wrapper(post_dest: PostDestination[UID, GID],
                          silently: bool,
                          **kwargs):
            await self.intercept(wrapped, post_dest=post_dest, silently=silently, **kwargs)

        return wrapper

    @abstractmethod
    async def intercept(self, wrapped_func: Callable, *,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        raise NotImplementedError()

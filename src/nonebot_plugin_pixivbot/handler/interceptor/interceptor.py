from abc import ABC
from functools import wraps
from typing import Callable, TypeVar, Generic

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.postman import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class Interceptor(ABC, Generic[UID, GID, B, M]):
    def __call__(self, wrapped: Callable):
        @wraps(wrapped)
        async def wrapper(post_dest: PostDestination[UID, GID, B, M],
                          silently: bool,
                          **kwargs):
            await self.intercept(wrapped, post_dest=post_dest, silently=silently, **kwargs)

        return wrapper

    async def intercept(self, wrapped_func: Callable,
                        post_dest: PostDestination[UID, GID, B, M],
                        silently: bool,
                        **kwargs):
        raise NotImplementedError()

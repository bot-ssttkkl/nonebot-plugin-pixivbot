from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager


@context.inject
class Interceptor(ABC):
    postman_manager = Inject(PostmanManager)

    async def post_plain_text(self, message: str,
                              post_dest: PostDestination[T_UID, T_GID]):
        await self.postman_manager.send_plain_text(message, post_dest=post_dest)

    @abstractmethod
    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        raise NotImplementedError()

    def __call__(self, wrapped: Callable):
        @wraps(wrapped)
        async def wrapper(*args, post_dest: PostDestination[T_UID, T_GID],
                          silently: bool,
                          **kwargs):
            await self.intercept(wrapped, *args, post_dest=post_dest, silently=silently, **kwargs)

        return wrapper

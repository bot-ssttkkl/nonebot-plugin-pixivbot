from asyncio import wait_for
from typing import TypeVar, Callable

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.inject
@context.register_singleton()
class TimeoutInterceptor(Interceptor):
    conf: Config

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        await wait_for(wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs),
                       timeout=self.conf.pixiv_query_timeout)


__all__ = ("TimeoutInterceptor",)

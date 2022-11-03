from asyncio import wait_for
from typing import Callable

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.handler.interceptor.base import Interceptor
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from ..pkg_context import context


@context.inject
@context.register_singleton()
class TimeoutInterceptor(Interceptor):
    conf = Inject(Config)

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        await wait_for(wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs),
                       timeout=self.conf.pixiv_query_timeout)


__all__ = ("TimeoutInterceptor",)

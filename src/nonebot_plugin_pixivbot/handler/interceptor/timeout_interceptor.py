from asyncio import wait_for
from typing import Callable, TYPE_CHECKING

from .base import Interceptor
from ..pkg_context import context
from ...config import Config

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler

conf = context.require(Config)


@context.register_singleton()
class TimeoutInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        await wait_for(wrapped_func(*args, **kwargs),
                       timeout=conf.pixiv_query_timeout)


__all__ = ("TimeoutInterceptor",)

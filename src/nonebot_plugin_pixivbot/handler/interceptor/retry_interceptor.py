import asyncio
from typing import Callable, TYPE_CHECKING

from aiohttp import ServerConnectionError
from nonebot import logger

from nonebot_plugin_pixivbot.global_context import context
from .base import Interceptor

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler

exception = (asyncio.TimeoutError, ServerConnectionError, ConnectionError)


@context.register_singleton()
class RetryInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        err = None

        for i in range(10):
            try:
                return await wrapped_func(*args, **kwargs)
            except exception as e:
                logger.error(f"Retrying... {i + 1}/10")
                logger.exception(e)
                err = e
            except Exception as e:
                raise e

        raise err

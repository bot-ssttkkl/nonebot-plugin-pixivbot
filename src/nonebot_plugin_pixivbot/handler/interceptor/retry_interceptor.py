import asyncio
from typing import Callable, TYPE_CHECKING

from aiohttp import ServerConnectionError
from nonebot import logger

from .base import Interceptor
from ...global_context import context

if TYPE_CHECKING:
    from ..base import Handler

exception = (asyncio.TimeoutError, ServerConnectionError, ConnectionError)


@context.register_singleton()
class RetryInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        err = None

        for i in range(10):
            try:
                return await wrapped_func(*args, **kwargs)
            except exception as e:
                logger.opt(exception=e).error(f"Network error occurred while handling, retrying... {i + 1}/10")
                err = e
            except Exception as e:
                raise e

        raise err

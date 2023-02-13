import asyncio
from typing import Callable

from aiohttp import ServerConnectionError
from nonebot import logger

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import Interceptor

exception = (asyncio.TimeoutError, ServerConnectionError, ConnectionError)


@context.inject
@context.register_singleton()
class RetryInterceptor(Interceptor):
    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        err = None

        for i in range(10):
            try:
                return await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
            except exception as e:
                logger.error(f"Retrying... {i + 1}/10")
                logger.exception(e)
                err = e
            except Exception as e:
                raise e

        raise err

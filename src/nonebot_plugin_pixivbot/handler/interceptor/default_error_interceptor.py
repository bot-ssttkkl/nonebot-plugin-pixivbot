import asyncio
from typing import Callable, TYPE_CHECKING

from aiohttp import ServerConnectionError
from nonebot import logger
from pixivpy_async.error import NoTokenError
from ssttkkl_nonebot_utils.errors.error_handler import ErrorHandlers

from nonebot_plugin_pixivbot.utils.errors import RateLimitError, PostIllustError
from .base import Interceptor
from ..pkg_context import context

if TYPE_CHECKING:
    from ..base import Handler

error_handlers = ErrorHandlers()


@error_handlers.register((NoTokenError,
                          RateLimitError,
                          asyncio.TimeoutError,
                          ServerConnectionError,
                          ConnectionError))
def _(e):
    logger.warning(e)
    return f"网络错误，请稍后再试（<{type(e).__name__}> {e}）"


@error_handlers.register(PostIllustError)
def _(e):
    logger.exception(e)
    return "图片发送失败了"


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        async def receive_error_message(msg: str):
            if not handler.silently:
                await handler.post_plain_text(msg)

        async with error_handlers.run_excepting(receive_error_message):
            await wrapped_func(*args, **kwargs)

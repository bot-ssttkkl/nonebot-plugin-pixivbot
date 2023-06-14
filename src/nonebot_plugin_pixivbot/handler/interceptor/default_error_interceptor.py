import asyncio
from typing import Callable, TYPE_CHECKING

from aiohttp import ServerConnectionError
from nonebot import logger
from nonebot.exception import ActionFailed
from pixivpy_async.error import NoTokenError

from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError, RateLimitError
from .base import Interceptor
from ..pkg_context import context

if TYPE_CHECKING:
    from ..base import Handler


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        try:
            await wrapped_func(*args, **kwargs)
        except (NoTokenError,
                RateLimitError,
                asyncio.TimeoutError,
                ServerConnectionError,
                ConnectionError) as e:
            logger.warning(e)
            if not handler.silently:
                await handler.post_plain_text(f"网络错误，请稍后再试（<{type(e).__name__}> {e}）")
        except (BadRequestError, QueryError) as e:
            if not handler.silently:
                await handler.post_plain_text(str(e))
        except ActionFailed as e:
            # 避免当发送消息错误时再尝试发送
            raise e
        except Exception as e:
            if not handler.silently:
                await handler.post_plain_text(f"内部错误：<{type(e).__name__}> {e}")
            raise e  # 重新抛出，让上层可以处理（如scheduler中需要处理Handler的异常）

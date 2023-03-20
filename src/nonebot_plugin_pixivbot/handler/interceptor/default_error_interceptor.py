import asyncio
from typing import Callable, TYPE_CHECKING

from aiohttp import ServerConnectionError
from nonebot import logger
from nonebot.exception import ActionFailed

from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError
from .base import Interceptor
from ..pkg_context import context

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        try:
            await wrapped_func(*args, **kwargs)
        except (asyncio.TimeoutError, ServerConnectionError, ConnectionError) as e:
            logger.warning(e)
            if not handler.silently:
                await handler.post_plain_text("网络错误")
        except (BadRequestError, QueryError) as e:
            if not handler.silently:
                await handler.post_plain_text(str(e))
        except ActionFailed as e:
            # 避免当发送消息错误时再尝试发送
            raise e
        except Exception as e:
            if not handler.silently:
                await handler.post_plain_text(f"内部错误：{type(e)}{e}")
            raise e  # 重新抛出，让上层可以处理（如scheduler中需要处理Handler的异常）

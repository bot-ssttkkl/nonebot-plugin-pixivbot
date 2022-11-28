import asyncio
from typing import Callable

from aiohttp import ServerConnectionError
from nonebot import logger
from nonebot.exception import ActionFailed

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError
from .base import Interceptor
from ..pkg_context import context


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):
    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        try:
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        except (asyncio.TimeoutError, ServerConnectionError, ConnectionError) as e:
            logger.warning(type(e).__name__)
            if not silently:
                await self.post_plain_text("网络错误", post_dest=post_dest)
        except (BadRequestError, QueryError) as e:
            if not silently:
                await self.post_plain_text(str(e), post_dest=post_dest)
        except ActionFailed as e:
            # 避免当发送消息错误时再尝试发送
            raise e
        except Exception as e:
            if not silently:
                await self.post_plain_text(f"内部错误：{type(e)}{e}", post_dest=post_dest)
            raise e  # 重新抛出，让上层可以处理（如scheduler中需要处理Handler的异常）

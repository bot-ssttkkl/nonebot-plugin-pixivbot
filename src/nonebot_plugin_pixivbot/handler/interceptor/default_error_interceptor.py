import asyncio
from typing import Callable, TypeVar

from nonebot import logger

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError
from .interceptor import Interceptor
from ...protocol_dep.postman import PostmanManager

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.inject
@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):
    postman_manager: PostmanManager

    async def post_plain_text(self, message: str,
                              post_dest: PostDestination):
        await self.postman_manager.send_plain_text(message, post_dest=post_dest)

    async def intercept(self, wrapped_func: Callable, *,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        try:
            await wrapped_func(post_dest=post_dest, silently=silently, **kwargs)
        except asyncio.TimeoutError:
            logger.warning("Timeout")
            if not silently:
                await self.post_plain_text(f"下载超时", post_dest=post_dest)
        except BadRequestError as e:
            if not silently:
                await self.post_plain_text(str(e), post_dest=post_dest)
        except QueryError as e:
            if not silently:
                await self.post_plain_text(str(e), post_dest=post_dest)
        except Exception as e:
            logger.exception(e)
            if not silently:
                await self.post_plain_text(f"内部错误：{type(e)}{e}", post_dest=post_dest)

import asyncio
from typing import Callable, TypeVar

from nonebot import logger
from nonebot.exception import ActionFailed

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError
from .interceptor import Interceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.inject
@context.register_singleton()
class DefaultErrorInterceptor(Interceptor):

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        try:
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
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
        except ActionFailed as e:
            # 避免当发送消息错误时再尝试发送
            raise e
        except Exception as e:
            if not silently:
                await self.post_plain_text(f"内部错误：{type(e)}{e}", post_dest=post_dest)
            raise e  # 重新抛出，让上层可以处理（如scheduler中需要处理Handler的异常）

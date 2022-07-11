from typing import Callable, TypeVar, Generic

from nonebot import Bot, logger
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import PostDestination, Postman
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor[UID, GID, B, M], Generic[UID, GID, B, M]):
    postman = context.require(Postman)

    async def intercept(self, wrapped_func: Callable,
                        post_dest: PostDestination[UID, GID, B, M],
                        silently: bool,
                        **kwargs):
        try:
            await wrapped_func(post_dest=post_dest, silently=silently, **kwargs)
        except TimeoutError:
            logger.warning("Timeout")
            if not silently:
                await self.postman.send_plain_text(f"下载超时", post_dest=post_dest)
        except BadRequestError as e:
            if not silently:
                await self.postman.send_plain_text(str(e), post_dest=post_dest)
        except QueryError as e:
            if not silently:
                await self.postman.send_plain_text(str(e), post_dest=post_dest)
        except Exception as e:
            logger.exception(e)
            if not silently:
                await self.postman.send_plain_text(f"内部错误：{type(e)}{e}", post_dest=post_dest)

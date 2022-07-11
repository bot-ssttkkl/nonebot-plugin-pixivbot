from typing import Callable, TypeVar, Generic

from nonebot import logger

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import PostDestination, Postman
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.register_singleton()
class DefaultErrorInterceptor(Interceptor[UID, GID], Generic[UID, GID]):
    postman = context.require(Postman)

    async def intercept(self, wrapped_func: Callable,
                        post_dest: PostDestination[UID, GID],
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

from typing import TYPE_CHECKING, Callable

from nonebot import logger
from nonebot_plugin_access_control.errors import PermissionDeniedError, RateLimitedError

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import Interceptor
from ..pkg_context import context
from ...config import Config
from ...context import Inject

if TYPE_CHECKING:
    from nonebot_plugin_access_control.service import Service


@context.inject
class ServiceInterceptor(Interceptor):
    conf: Config = Inject(Config)

    def __init__(self, service: "Service", *, acquire_rate_limit_token: bool = True):
        self.service = service
        self.acquire_rate_limit_token = acquire_rate_limit_token

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        reply = None

        subjects = post_dest.extract_subjects()
        try:
            await self.service.check_by_subject(*subjects, throw_on_fail=True,
                                                acquire_rate_limit_token=self.acquire_rate_limit_token)
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        except PermissionDeniedError:
            logger.debug(f"permission denied {post_dest}")
            reply = self.conf.access_control_reply_on_permission_denied
        except RateLimitedError:
            logger.debug(f"rate limited {post_dest}")
            reply = self.conf.access_control_reply_on_rate_limited

        if not silently and reply:
            await self.post_plain_text(reply, post_dest=post_dest)

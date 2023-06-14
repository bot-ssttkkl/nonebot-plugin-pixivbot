from typing import TYPE_CHECKING, Callable

from nonebot import get_bot
from nonebot_plugin_access_control.errors import PermissionDeniedError, RateLimitedError
from nonebot_plugin_access_control.subject import extract_subjects, extract_subjects_from_session

from .base import Interceptor
from ..pkg_context import context
from ...config import Config

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler
    from nonebot_plugin_access_control.service import Service

conf = context.require(Config)


class ServiceInterceptor(Interceptor):
    def __init__(self, service: "Service", *, acquire_rate_limit_token: bool = True):
        self.service = service
        self.acquire_rate_limit_token = acquire_rate_limit_token

    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        reply = None

        if handler.event is not None:
            subjects = extract_subjects(get_bot(handler.session.bot_id), handler.event)
        else:
            subjects = extract_subjects_from_session(handler.session)

        try:
            await self.service.check_by_subject(*subjects, throw_on_fail=True,
                                                acquire_rate_limit_token=self.acquire_rate_limit_token)
            await wrapped_func(*args, **kwargs)
        except PermissionDeniedError:
            reply = conf.access_control_reply_on_permission_denied
        except RateLimitedError:
            reply = conf.access_control_reply_on_rate_limited

        if not handler.silently and reply:
            await handler.post_plain_text(reply)

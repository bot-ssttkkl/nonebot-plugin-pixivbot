from typing import Callable, TYPE_CHECKING

from ssttkkl_nonebot_utils.platform import platform_func

from .base import Interceptor
from ..pkg_context import context
from ...config import Config

if TYPE_CHECKING:
    from ..base import Handler

conf = context.require(Config)


@context.register_singleton()
class LoadingPromptInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        if handler.silently or not platform_func.is_supported(handler.session.bot_type, "handling_reaction"):
            await wrapped_func(*args, **kwargs)
        else:
            async with platform_func(handler.session.bot_type).handling_reaction(handler.session, handler.event):
                await wrapped_func(*args, **kwargs)

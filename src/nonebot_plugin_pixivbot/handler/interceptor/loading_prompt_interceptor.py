from typing import Callable, TYPE_CHECKING

from nonebot import get_bot
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
        if handler.silently:
            await wrapped_func(*args, **kwargs)
        else:
            bot = get_bot(handler.session.bot_id)
            async with platform_func(handler.session.bot_type).handling_reaction(bot, handler.event):
                await wrapped_func(*args, **kwargs)

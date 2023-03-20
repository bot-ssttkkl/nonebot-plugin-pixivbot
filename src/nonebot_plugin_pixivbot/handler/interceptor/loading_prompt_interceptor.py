from asyncio import create_task, sleep, shield, Task
from typing import Callable, Optional, TYPE_CHECKING

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from .base import Interceptor
from ..pkg_context import context

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler

conf = context.require(Config)


@context.register_singleton()
class LoadingPromptInterceptor(Interceptor):

    async def send_delayed_loading_prompt(self, handler: "Handler"):
        await sleep(conf.pixiv_loading_prompt_delayed_time)

        logger.debug(f"send delayed loading to {handler.post_dest.identifier}")
        await shield(handler.post_plain_text("努力加载中"))

    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        task: Optional[Task] = None
        if not handler.silently:
            task = create_task(self.send_delayed_loading_prompt(handler))

        try:
            await wrapped_func(*args, **kwargs)
        finally:
            if task and not task.done():
                task.cancel()

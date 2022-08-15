from asyncio import create_task, sleep, shield, Task
from typing import Callable, Optional

from nonebot import logger

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .interceptor import Interceptor, UID, GID


@context.register_singleton()
class LoadingInterceptor(Interceptor):
    async def send_delayed_loading(self, post_dest: PostDestination[UID, GID]):
        await sleep(3.0)
        logger.debug(f"send delayed loading to {post_dest.identifier}")
        await shield(self.post_plain_text("努力加载中", post_dest))

    async def intercept(self, wrapped_func: Callable,
                        *args, post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        task: Optional[Task] = None
        if not silently:
            task = create_task(self.send_delayed_loading(post_dest))

        try:
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        finally:
            if task and not task.done():
                task.cancel()

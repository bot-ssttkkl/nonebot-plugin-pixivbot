from datetime import datetime
from math import ceil
from typing import TypeVar, Generic, Callable

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import PostDestination, Postman

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.register_singleton()
class CooldownInterceptor(Interceptor[UID, GID], Generic[UID, GID]):
    conf = context.require(Config)
    postman = context.require(Postman)

    def __init__(self):
        self.last_query_time = dict[UID, datetime]()

    def get_cooldown(self, user_id: UID) -> int:
        if self.conf.pixiv_query_cooldown == 0 or user_id in self.conf.pixiv_no_query_cooldown_users:
            return 0

        now = datetime.now()
        if user_id not in self.last_query_time:
            self.last_query_time[user_id] = now
            return 0
        else:
            delta = now - self.last_query_time[user_id]
            cooldown = self.conf.pixiv_query_cooldown - ceil(delta.total_seconds())
            if cooldown > 0:
                return cooldown
            else:
                self.last_query_time[user_id] = now
                return 0

    async def intercept(self, wrapped_func: Callable,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        cooldown = self.get_cooldown(post_dest.user_id)
        if cooldown:
            if not silently:
                await self.postman.send_plain_text(f"你的CD还有{cooldown}s转好", post_dest=post_dest)
        else:
            await wrapped_func(post_dest=post_dest, silently=silently, **kwargs)


__all__ = ("CooldownInterceptor",)

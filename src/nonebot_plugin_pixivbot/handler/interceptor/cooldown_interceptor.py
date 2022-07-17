from datetime import datetime
from math import ceil
from typing import TypeVar, Generic

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import PermissionInterceptor
from nonebot_plugin_pixivbot.postman import PostDestination
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.register_singleton()
class CooldownInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def __init__(self):
        self.conf = context.require(Config)
        self.last_query_time = dict[UID, datetime]()

    def has_permission(self, post_dest: PostDestination[UID, GID]) -> bool:
        if self.conf.pixiv_query_cooldown == 0:
            return True

        if str(post_dest.user_id) in self.conf.pixiv_no_query_cooldown_users \
                or f"{get_adapter_name()}:{post_dest.user_id}" in self.conf.pixiv_no_query_cooldown_users:
            return True

        now = datetime.now()
        if post_dest.user_id not in self.last_query_time:
            self.last_query_time[post_dest.user_id] = now
            return True
        else:
            delta = now - self.last_query_time[post_dest.user_id]
            cooldown = self.conf.pixiv_query_cooldown - ceil(delta.total_seconds())
            if cooldown > 0:
                return False
            else:
                self.last_query_time[post_dest.user_id] = now
                return True

    def get_permission_denied_msg(self, post_dest: PostDestination[UID, GID]) -> str:
        now = datetime.now()
        delta = now - self.last_query_time[post_dest.user_id]
        cooldown = self.conf.pixiv_query_cooldown - ceil(delta.total_seconds())
        return f"你的CD还有{cooldown}s转好"


__all__ = ("CooldownInterceptor",)

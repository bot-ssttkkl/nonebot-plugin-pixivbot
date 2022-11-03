from datetime import datetime, timezone
from math import ceil

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model import UserIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .permission_interceptor import PermissionInterceptor
from ..pkg_context import context


@context.inject
@context.register_singleton()
class CooldownInterceptor(PermissionInterceptor):
    conf = Inject(Config)

    def __init__(self):
        super().__init__()
        self.last_query_time = dict[UserIdentifier[T_UID], datetime]()

    def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        if self.conf.pixiv_query_cooldown == 0:
            return True

        if not post_dest.user_id:
            logger.debug("cooldown intercept was skipped for group post")
            return True

        identifier = UserIdentifier(post_dest.adapter, post_dest.user_id)

        if str(post_dest.user_id) in self.conf.pixiv_no_query_cooldown_users \
                or str(identifier) in self.conf.pixiv_no_query_cooldown_users:
            return True

        now = datetime.now(timezone.utc)
        if identifier not in self.last_query_time:
            self.last_query_time[identifier] = now
            return True
        else:
            logger.debug(f"last query time ({identifier}): {self.last_query_time[identifier]}")
            delta = now - self.last_query_time[identifier]
            cooldown = self.conf.pixiv_query_cooldown - delta.total_seconds()
            if cooldown > 0:
                logger.debug(f"cooldown ({identifier}): {cooldown}s")
                return False
            else:
                self.last_query_time[identifier] = now
                return True

    def get_permission_denied_msg(self, post_dest: PostDestination[T_UID, T_GID]) -> str:
        identifier = UserIdentifier(post_dest.adapter, post_dest.user_id)
        now = datetime.now(timezone.utc)
        delta = now - self.last_query_time[identifier]
        cooldown = ceil(self.conf.pixiv_query_cooldown - delta.total_seconds())
        return f"你的CD还有{cooldown}s转好"


__all__ = ("CooldownInterceptor",)

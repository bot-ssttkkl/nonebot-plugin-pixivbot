from nonebot import get_driver
from pydantic import BaseSettings

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot_kook.enums import KookAdminStrategy


@context.register_singleton(**get_driver().config.dict())
class KookConfig(BaseSettings):
    pixiv_kook_admin_strategy = KookAdminStrategy.nobody
    pixiv_kook_admin_must_have_permission = 0
    pixiv_kook_admin_permission_cache_ttl = 60 * 60 * 2

    class Config:
        extra = "ignore"


__all__ = ("KookConfig",)

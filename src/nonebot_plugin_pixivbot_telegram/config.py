from nonebot import get_driver
from pydantic import BaseSettings

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot_kook.enums import KookAdminStrategy


@context.register_singleton(**get_driver().config.dict())
class TelegramConfig(BaseSettings):
    pixiv_telegram_admin_permission_cache_ttl = 60 * 60 * 2

    class Config:
        extra = "ignore"


__all__ = ("TelegramConfig",)

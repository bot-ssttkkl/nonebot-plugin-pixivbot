from nonebot import get_driver, logger
from pydantic import BaseSettings, root_validator

from nonebot_plugin_pixivbot.global_context import context


def _deprecated_warn(name: str):
    logger.warning(f"config \"{name}\" is deprecated, use nonebot-plugin-access-control instead "
                   "(MORE INFO: https://github.com/ssttkkl/nonebot-plugin-pixivbot#%E6%9D%83%E9%99%90%E6%8E%A7%E5%88%B6)")


@context.register_singleton(**get_driver().config.dict())
class KookConfig(BaseSettings):
    @root_validator(pre=True, allow_reuse=True)
    def deprecated_config(cls, values):
        for name in {"pixiv_kook_admin_strategy", "pixiv_kook_admin_must_have_permission"}:
            if name in values:
                _deprecated_warn(name)
        return values

    class Config:
        extra = "ignore"


__all__ = ("KookConfig",)

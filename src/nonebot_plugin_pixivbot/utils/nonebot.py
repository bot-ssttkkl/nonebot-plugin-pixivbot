from typing import Optional

from nonebot import Bot, get_bot, get_driver

from nonebot_plugin_pixivbot.model import UserIdentifier


def get_adapter_name(bot: Optional[Bot] = None) -> str:
    if not bot:
        bot = get_bot()
    return bot.adapter.get_name().split(maxsplit=1)[0].lower()


default_command_start: str = next(iter(get_driver().config.command_start))


def get_bot_user_identifier(bot: Bot) -> UserIdentifier[str]:
    return UserIdentifier(get_adapter_name(bot), bot.self_id)


def is_superuser(bot: Bot, user_id: any) -> bool:
    return (
            f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{user_id}"
            in bot.config.superusers
            or user_id in bot.config.superusers  # 兼容旧配置
    )

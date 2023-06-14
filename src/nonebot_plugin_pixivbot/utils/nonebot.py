from typing import Optional

from nonebot import Bot, get_bot, get_driver


def get_adapter_name(bot: Optional[Bot] = None) -> str:
    if not bot:
        bot = get_bot()
    return bot.adapter.get_name().split(maxsplit=1)[0].lower()


default_command_start: str = next(iter(get_driver().config.command_start))

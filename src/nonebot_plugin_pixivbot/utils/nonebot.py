from typing import Optional

from nonebot import Bot, get_bot


def get_adapter_name(bot: Optional[Bot] = None) -> str:
    if not bot:
        bot = get_bot()
    return bot.adapter.get_name().split(maxsplit=1)[0].lower()

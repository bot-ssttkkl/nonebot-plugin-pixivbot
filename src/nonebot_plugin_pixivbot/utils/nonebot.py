from typing import Optional

from nonebot import Bot, get_bot, get_driver, get_bots

from nonebot_plugin_pixivbot.model import UserIdentifier


def get_adapter_name(bot: Optional[Bot] = None) -> str:
    if not bot:
        bot = get_bot()
    return bot.adapter.get_name().split(maxsplit=1)[0].lower()


default_command_start: str = next(iter(get_driver().config.command_start))


def get_bot_by_adapter(adapter: str) -> Optional[Bot]:
    # TODO: 当同时连接多个同一adapter的bot时插件无法正常工作
    for b in get_bots().values():
        if get_adapter_name(b) == adapter:
            return b

    return None


def get_bot_user_identifier(bot: Bot) -> UserIdentifier[str]:
    return UserIdentifier(get_adapter_name(bot), bot.self_id)

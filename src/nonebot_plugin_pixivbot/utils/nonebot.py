from nonebot import Bot


def get_adapter_name(bot: Bot) -> str:
    return bot.adapter.get_name().split(maxsplit=1)[0].lower()

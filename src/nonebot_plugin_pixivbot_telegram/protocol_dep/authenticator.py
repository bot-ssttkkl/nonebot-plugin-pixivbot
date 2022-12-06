from typing import List, Optional

from asyncache import cached
from cachetools import TTLCache
from nonebot import get_bot
from nonebot.adapters.telegram.exception import TelegramAdapterException

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager, \
    Authenticator as BaseAuthenticator
from .post_dest import PostDestination
from ..config import TelegramConfig

conf = context.require(TelegramConfig)


async def get_chat(bot_id: str, chat_id: int) -> Optional[dict]:
    bot = get_bot(bot_id)
    try:
        result = await bot.get_chat(chat_id=chat_id)
        if result['ok']:
            return result['result']
        else:
            return None
    except TelegramAdapterException:
        # 目前tg适配器请求失败抛出的是NetworkError，但是按照定义应该抛出ActionFailed
        # https://github.com/nonebot/adapter-telegram/issues/19
        return None


async def get_chat_admin(bot_id: str, chat_id: int) -> List[dict]:
    bot = get_bot(bot_id)
    result = await bot.get_chat_administrators(chat_id=chat_id)
    if result['ok']:
        return result['result']
    else:
        return []


if conf.pixiv_telegram_admin_permission_cache_ttl > 0:
    get_chat = cached(TTLCache(maxsize=128, ttl=conf.pixiv_telegram_admin_permission_cache_ttl))(get_chat)
    get_chat_admin = cached(TTLCache(maxsize=128, ttl=conf.pixiv_telegram_admin_permission_cache_ttl))(get_chat_admin)


@context.require(AuthenticatorManager).register
class Authenticator(BaseAuthenticator):
    @classmethod
    def adapter(cls) -> str:
        return "telegram"

    async def group_admin(self, post_dest: PostDestination) -> bool:
        admins = await get_chat_admin(post_dest.bot.self_id, post_dest.chat_id)
        for admin in admins:
            if admin['user']['id'] == post_dest.user_id:
                return True
        return False

    async def available(self, post_dest: PostDestination) -> bool:
        chat = await get_chat(post_dest.bot.self_id, post_dest.chat_id)
        return chat is not None


__all__ = ("Authenticator",)

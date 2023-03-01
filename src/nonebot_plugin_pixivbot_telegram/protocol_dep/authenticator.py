from typing import Optional

from asyncache import cached
from cachetools import TTLCache
from nonebot import get_bot
from nonebot.adapters.telegram.exception import ActionFailed

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager, \
    Authenticator as BaseAuthenticator
from .post_dest import PostDestination

cache_ttl = 60 * 60 * 2


@cached(TTLCache(maxsize=128, ttl=cache_ttl))
async def get_chat(bot_id: str, chat_id: int) -> Optional[dict]:
    bot = get_bot(bot_id)
    try:
        result = await bot.get_chat(chat_id=chat_id)
        if result['ok']:
            return result['result']
        else:
            return None
    except ActionFailed:
        return None


@context.register_singleton()
class Authenticator(BaseAuthenticator, manager=AuthenticatorManager):
    adapter = "telegram"

    async def available(self, post_dest: PostDestination) -> bool:
        chat = await get_chat(post_dest.bot.self_id, post_dest.chat_id)
        return chat is not None


__all__ = ("Authenticator",)

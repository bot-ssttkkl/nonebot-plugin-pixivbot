from typing import Dict, Tuple

from asyncache import cached
from cachetools import TTLCache
from nonebot import logger, get_bot
from nonebot.adapters.kaiheila.exception import ActionFailed

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager, \
    Authenticator as BaseAuthenticator
from .post_dest import PostDestination, ChannelPostDestination, PrivatePostDestination
from ..config import KookConfig
from ..enums import KookAdminStrategy

conf = context.require(KookConfig)


async def get_guild_roles(bot_id: str, guild_id: str) -> Dict[int, int]:
    """
    获取服务器角色权限

    :param bot_id:
    :param guild_id:
    :return: 代表服务器角色权限的字典，key为role_id，value为permissions
    """
    bot = get_bot(bot_id)

    logger.debug(f"request guild {guild_id} roles")
    guild_roles = {}

    page = -1
    page_size = -1
    page_total = 2 ** 31

    while page <= page_total:
        query = {"guild_id": guild_id}
        if page != -1:
            query["page"] = page
        if page_size != -1:
            query["page_size"] = page_size

        guild_role_list = await bot.call_api("guild-role/list", query=query)
        for role in guild_role_list["items"]:
            guild_roles[role["role_id"]] = role["permissions"]

        page = guild_role_list["meta"]["page"] + 1
        page_size = guild_role_list["meta"]["page_size"]
        page_total = guild_role_list["meta"]["page_total"]

    return guild_roles


async def get_channel_overwrites(bot_id: str, channel_id: str) \
        -> Tuple[Dict[int, Tuple[bool, bool]], Dict[int, Tuple[bool, bool]]]:
    """
    获取频道覆写权限

    :param bot_id:
    :param channel_id:
    :return: {role_id: [allow], [deny]}, {user_id: [allow], [deny]}
    """
    bot = get_bot(bot_id)
    logger.debug(f"request channel {channel_id} overwrites")
    channel_roles = await bot.call_api("channel-role/index", query={"channel_id": channel_id})

    role_overwrites = {}
    for ow in channel_roles["permission_overwrites"]:
        role_id = ow["role_id"]
        role_overwrites[role_id] = ow["allow"], ow["deny"]

    user_overwrites = {}
    for ow in channel_roles["permission_users"]:
        user_id = ow["user"]["id"]
        role_overwrites[user_id] = ow["allow"], ow["deny"]

    return role_overwrites, user_overwrites


async def get_user_permissions(bot_id: str, user_id: str, channel_id: str, guild_id: str) -> int:
    """
    获取用户在该服务器该频道的权限

    :param bot_id:
    :param user_id:
    :param channel_id:
    :param guild_id:
    :return: 代表权限的掩码值（参考 https://developer.kaiheila.cn/doc/http/guild-role）
    """
    bot = get_bot(bot_id)

    logger.debug(f"request user {user_id} view in guild {guild_id}")
    user_view = await bot.call_api("user/view", query={
        "user_id": user_id,
        "guild_id": guild_id
    })

    if "roles" in user_view and len(user_view["roles"]) > 0:
        guild_roles = await get_guild_roles(bot_id, guild_id)
        role_overwrites, user_overwrites = await get_channel_overwrites(bot.self_id, channel_id)

        permissions = 0
        for role_id, role_permissions in guild_roles.items():
            # 覆写角色权限
            if role_id in role_overwrites:
                role_permissions |= role_overwrites[role_id][0]
                role_permissions &= -1 ^ role_overwrites[role_id][1]

            if role_id in user_view["roles"]:
                permissions |= role_permissions

        # 覆写用户权限
        for user_id in user_overwrites:
            if user_id == user_id:
                permissions |= user_overwrites[user_id][0]
                permissions &= -1 ^ user_overwrites[user_id][1]

        return permissions
    else:
        return 0


if conf.pixiv_kook_admin_permission_cache_ttl > 0:
    get_guild_roles = cached(TTLCache(maxsize=16, ttl=conf.pixiv_kook_admin_permission_cache_ttl))(
        get_guild_roles)
    get_channel_overwrites = cached(TTLCache(maxsize=16, ttl=conf.pixiv_kook_admin_permission_cache_ttl))(
        get_channel_overwrites)
    get_user_permissions = cached(TTLCache(maxsize=16, ttl=conf.pixiv_kook_admin_permission_cache_ttl))(
        get_user_permissions)


@context.require(AuthenticatorManager).register
class Authenticator(BaseAuthenticator):

    @classmethod
    def adapter(cls) -> str:
        return "kaiheila"

    async def group_admin(self, post_dest: PostDestination) -> bool:
        if conf.pixiv_kook_admin_strategy == KookAdminStrategy.everyone:
            return True
        elif conf.pixiv_kook_admin_strategy == KookAdminStrategy.nobody:
            return False
        elif conf.pixiv_kook_admin_strategy == KookAdminStrategy.must_have_permission:
            if not isinstance(post_dest, ChannelPostDestination):
                raise ValueError("expect ChannelPostDestination, got " + str(type(post_dest)))

            if not post_dest.guild_id:
                logger.warning("unable to authenticate without guild_id")
                return False

            permissions = await get_user_permissions(post_dest.bot.self_id,
                                                     post_dest.user_id,
                                                     post_dest.channel_id,
                                                     post_dest.guild_id)
            logger.debug(f"user: {post_dest.user_id} guild: {post_dest.guild_id} permissions: {permissions}")
            return conf.pixiv_kook_admin_must_have_permission & permissions == \
                   conf.pixiv_kook_admin_must_have_permission
        else:
            raise ValueError("invalid KookAdminStrategy value: " + conf.pixiv_kook_admin_strategy)

    async def available(self, post_dest: PostDestination) -> bool:
        if isinstance(post_dest, ChannelPostDestination):
            try:
                permissions = await get_user_permissions(post_dest.bot.self_id,
                                                         post_dest.user_id,
                                                         post_dest.channel_id,
                                                         post_dest.guild_id)
                return (permissions & 4096) != 0  # 有在该频道发送消息的权限
            except ActionFailed:
                return False
        elif isinstance(post_dest, PrivatePostDestination):
            try:
                # 尝试发起私聊，若能够成功发起则说明可用
                result = await post_dest.bot.call_api("user-chat/create", target_id=post_dest.user_id)
                return True
            except ActionFailed:
                return False


__all__ = ("Authenticator",)

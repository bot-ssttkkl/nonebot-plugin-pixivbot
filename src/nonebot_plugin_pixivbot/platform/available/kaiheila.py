from typing import Dict, Tuple

from nonebot import logger, get_bot
from nonebot.adapters.kaiheila.exception import ActionFailed
from nonebot_plugin_session import Session, SessionLevel


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


async def available(session: Session) -> bool:
    try:
        if session.level != SessionLevel.LEVEL1:
            permissions = await get_user_permissions(session.bot_id,
                                                     session.id1,
                                                     session.id2,
                                                     session.id3)
            return (permissions & 4096) != 0  # 有在该频道发送消息的权限
        else:
            bot = get_bot(session.bot_id)
            # 尝试发起私聊，若能够成功发起则说明可用
            result = await bot.call_api("user-chat/create", target_id=session.id1)
            return True
    except ActionFailed:
        return False

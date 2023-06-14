from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot
from nonebot.exception import ActionFailed
from nonebot_plugin_session import Session


async def available(session: Session) -> bool:
    bot: Bot = get_bot(session.bot_id)
    try:
        if session.id2 is not None:
            group_info = await bot.get_group_info(group_id=int(session.id2))
            # 如果机器人尚未加入群, group_create_time, group_level, max_member_count 和 member_count 将会为0
            return group_info["member_count"] != 0
        else:
            friend_list = await bot.get_friend_list()
            for friend in friend_list:
                if friend["user_id"] == session.id1:
                    return True
            return False
    except ActionFailed:
        return False

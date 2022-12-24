from typing import Union, Awaitable

from nonebot.adapters.onebot.v11 import ActionFailed

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.authenticator import Authenticator as BaseAuthenticator, \
    AuthenticatorManager
from nonebot_plugin_pixivbot_onebot_v11.protocol_dep.post_dest import PostDestination


@context.require(AuthenticatorManager).register
class Authenticator(BaseAuthenticator):
    @classmethod
    def adapter(cls) -> str:
        return "onebot"

    async def group_admin(self, post_dest: PostDestination) -> bool:
        result = await post_dest.bot.get_group_member_info(group_id=post_dest.group_id, user_id=post_dest.user_id)
        return result["role"] == "owner" or result["role"] == "admin"

    async def available(self, post_dest: PostDestination) -> Union[bool, Awaitable[bool]]:
        try:
            if post_dest.group_id is not None:
                group_info = await post_dest.bot.get_group_info(group_id=post_dest.group_id)
                # 如果机器人尚未加入群, group_create_time, group_level, max_member_count 和 member_count 将会为0
                return group_info["member_count"] != 0
            else:
                friend_list = await post_dest.bot.get_friend_list()
                for friend in friend_list:
                    if friend["user_id"] == post_dest.user_id:
                        return True
                return False
        except ActionFailed:
            return False

from typing import Union, Awaitable, TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.cmd.command_handler import SubCommandHandler, CommandHandler
from nonebot_plugin_pixivbot.postman import PostDestination, PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.require(CommandHandler).sub_command("help")
class HelpHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    help_text = """常规语句：
- 看看榜<范围>：查看pixiv榜单
- 来张图：从推荐插画随机抽选一张插画
- 来张<关键字>图：搜索关键字，从搜索结果随机抽选一张插画
- 来张<用户>老师的图：搜索画师，从该画师的插画列表里随机抽选一张插画
- 看看图<插画ID>：查看id为<插画ID>的插画
- 来张私家车：从书签中随机抽选一张插画
- 还要：重复上一次请求
- 不够色：获取上一张插画的相关推荐

命令语句：
- /pixivbot help：查看本帮助
- /pixivbot bind：绑定Pixiv账号

更多功能：参见https://github.com/ssttkkl/PixivBot
"""

    @classmethod
    def type(cls) -> str:
        return "help"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) \
            -> Union[dict, Awaitable[dict]]:
        return {}

    async def actual_handle(self, *, post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        await self.postman.send_message(self.help_text, post_dest=post_dest)
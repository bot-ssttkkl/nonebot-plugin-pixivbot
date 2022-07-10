from typing import TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.data.pixiv import PixivRepo
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.cmd.command_handler import SubCommandHandler, CommandHandler
from nonebot_plugin_pixivbot.postman import PostIdentifier, PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.require(CommandHandler).sub_command("invalidate_cache")
class InvalidateCacheHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    pixiv_data_source = context.require(PixivRepo)

    @classmethod
    def type(cls) -> str:
        return "invalidate_cache"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {}

    async def actual_handle(self, *, post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        if post_dest.user_id not in post_dest.bot.config.superusers:
            await self.postman.send_message(message="只有超级用户可以调用该命令", post_dest=post_dest)
            return

        await self.pixiv_data_source.invalidate_cache()
        await self.postman.send_message(message="ok", post_dest=post_dest)

from typing import TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.cmd.command_handler import SubCommandHandler, CommandHandler
from nonebot_plugin_pixivbot.postman import PostDestination, PostIdentifier
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.require(CommandHandler).sub_command("bind")
class BindHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    binder = context.require(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "bind"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        if len(args) < 1:
            raise BadRequestError()
        else:
            pixiv_user_id = int(args[0])
            return {"pixiv_user_id": pixiv_user_id}

    async def actual_handle(self, *, pixiv_user_id: int,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        await self.binder.bind(post_dest.bot, post_dest.user_id, pixiv_user_id)
        await self.postman.send_message(message="Pixiv账号绑定成功", post_dest=post_dest)

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID, B, M]):
        pixiv_user_id = await self.binder.get_binding(post_dest.bot, post_dest.user_id)
        if pixiv_user_id is not None:
            msg = f"当前绑定账号：{pixiv_user_id}\n"
        else:
            msg = "当前未绑定Pixiv账号\n"
        msg += "命令格式：/pixivbot bind <pixiv_user_id>"
        await self.postman.send_message(message=msg, post_dest=post_dest)


@context.require(CommandHandler).sub_command("unbind")
class UnbindHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    binder = context.require(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "unbind"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {}

    async def actual_handle(self, *, post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        await self.binder.unbind(post_dest.bot, post_dest.user_id)
        await self.postman.send_message(message="Pixiv账号解绑成功", post_dest=post_dest)

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID, B, M]):
        await self.postman.send_message(message="当前未绑定Pixiv账号", post_dest=post_dest)

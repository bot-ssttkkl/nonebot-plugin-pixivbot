from typing import TypeVar, Sequence, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import SubCommandHandler, CommandHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.require(CommandHandler).sub_command("bind")
class BindHandler(SubCommandHandler):
    def __init__(self):
        super().__init__()
        self.binder = context.require(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "bind"

    def enabled(self) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        if len(args) < 1:
            raise BadRequestError()
        else:
            pixiv_user_id = int(args[0])
            return {"pixiv_user_id": pixiv_user_id}

    async def actual_handle(self, *, pixiv_user_id: int,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.binder.bind(post_dest.adapter, post_dest.user_id, pixiv_user_id)
        await self.post_plain_text(message="Pixiv账号绑定成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        pixiv_user_id = await self.binder.get_binding(post_dest.adapter, post_dest.user_id)
        if pixiv_user_id is not None:
            msg = f"当前绑定账号：{pixiv_user_id}\n"
        else:
            msg = "当前未绑定Pixiv账号\n"
        msg += "命令格式：/pixivbot bind <pixiv_user_id>"
        await self.post_plain_text(message=msg, post_dest=post_dest)


@context.require(CommandHandler).sub_command("unbind")
class UnbindHandler(SubCommandHandler):
    def __init__(self):
        super().__init__()
        self.binder = context.require(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "unbind"

    def enabled(self) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        return {}

    async def actual_handle(self, *, post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.binder.unbind(post_dest.adapter, post_dest.user_id)
        await self.post_plain_text(message="Pixiv账号解绑成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        await self.post_plain_text(message="当前未绑定Pixiv账号", post_dest=post_dest)

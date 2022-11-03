from typing import Sequence

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import SubCommandHandler, CommandHandler
from ..pkg_context import context
from ... import default_command_start


@context.inject
@context.require(CommandHandler).sub_command("bind")
class BindHandler(SubCommandHandler):
    binder = Inject(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "bind"

    def enabled(self) -> bool:
        return True

    async def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        if len(args) < 1:
            raise BadRequestError()
        else:
            try:
                pixiv_user_id = int(args[0])
            except ValueError as e:
                raise BadRequestError("请输入正确格式的Pixiv账号") from e

            return {"pixiv_user_id": pixiv_user_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, pixiv_user_id: int,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        await self.binder.bind(post_dest.adapter, post_dest.user_id, pixiv_user_id)
        await self.post_plain_text(message="Pixiv账号绑定成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[T_UID, T_GID],
                                        silently: bool = False):
        if not silently:
            if err.message:
                await self.post_plain_text(message=err.message, post_dest=post_dest)
            else:
                pixiv_user_id = await self.binder.get_binding(post_dest.adapter, post_dest.user_id)
                if pixiv_user_id is not None:
                    msg = f"当前绑定账号：{pixiv_user_id}\n"
                else:
                    msg = "当前未绑定Pixiv账号\n"
                msg += f"命令格式：{default_command_start}pixivbot bind <pixiv_user_id>"
                await self.post_plain_text(message=msg, post_dest=post_dest)


@context.inject
@context.require(CommandHandler).sub_command("unbind")
class UnbindHandler(SubCommandHandler):
    binder = Inject(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "unbind"

    def enabled(self) -> bool:
        return True

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        return {}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        result = await self.binder.unbind(post_dest.adapter, post_dest.user_id)
        if result:
            await self.post_plain_text(message="Pixiv账号解绑成功", post_dest=post_dest)
        else:
            await self.post_plain_text(message="当前未绑定Pixiv账号", post_dest=post_dest)

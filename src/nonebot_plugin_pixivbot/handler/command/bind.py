from typing import Sequence

from .subcommand import SubCommandHandler
from ..pkg_context import context
from ...plugin_service import bind_service
from ...service.pixiv_account_binder import PixivAccountBinder
from ...utils.errors import BadRequestError
from ...utils.nonebot import default_command_start

binder = context.require(PixivAccountBinder)


class BindHandler(SubCommandHandler, subcommand='bind', service=bind_service):
    @classmethod
    def type(cls) -> str:
        return "bind"

    async def parse_args(self, args: Sequence[str]) -> dict:
        if len(args) < 1:
            raise BadRequestError()
        else:
            try:
                pixiv_user_id = int(args[0])
            except ValueError as e:
                raise BadRequestError("请输入正确格式的Pixiv账号") from e

            return {"pixiv_user_id": pixiv_user_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, pixiv_user_id: int):
        await binder.bind(self.session.platform, self.session.id1, pixiv_user_id)
        await self.post_plain_text(message="Pixiv账号绑定成功")

    async def actual_handle_bad_request(self, err: BadRequestError):
        if not self.silently:
            if err.message:
                await self.post_plain_text(message=err.message)
            else:
                pixiv_user_id = await binder.get_binding(self.session.platform, self.session.id1)
                if pixiv_user_id is not None:
                    msg = f"当前绑定账号：{pixiv_user_id}\n"
                else:
                    msg = "当前未绑定Pixiv账号\n"
                msg += f"命令格式：{default_command_start}pixivbot bind <pixiv_user_id>"
                await self.post_plain_text(message=msg)


class UnbindHandler(SubCommandHandler, subcommand='unbind', service=bind_service):
    @classmethod
    def type(cls) -> str:
        return "unbind"

    # noinspection PyMethodOverriding
    async def actual_handle(self):
        result = await binder.unbind(self.session.platform, self.session.id1)
        if result:
            await self.post_plain_text(message="Pixiv账号解绑成功")
        else:
            await self.post_plain_text(message="当前未绑定Pixiv账号")

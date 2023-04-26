from io import StringIO
from typing import Sequence

from nonebot_plugin_pixivbot.model import WatchType, T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import manage_watch_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from nonebot_plugin_pixivbot.service.watchman import Watchman
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.nonebot import default_command_start
from .subcommand import SubCommandHandler
from ..pkg_context import context

watchman = context.require(Watchman)
pixiv = context.require(PixivService)


async def parse_and_get_user(raw_user: str):
    # try parse
    try:
        user = int(raw_user)
        return await pixiv.get_user(user)
    except ValueError:
        return await pixiv.get_user(raw_user)


async def build_tasks_msg(post_dest: PostDestination[T_UID, T_GID]):
    tasks = [x async for x in watchman.get_by_subscriber(post_dest)]
    with StringIO() as sio:
        sio.write("当前订阅：\n")
        if len(tasks) > 0:
            for t in tasks:
                sio.write(f'[{t.code}] {t.type.name}')
                args_text = t.args_text
                if args_text:
                    sio.write(f' ({args_text})')
                sio.write('\n')
        else:
            sio.write('无\n')
        return sio.getvalue()


async def parse_user_illusts_args(args: Sequence[str]):
    if len(args) < 2:
        raise BadRequestError()

    user = await parse_and_get_user(args[1])

    watch_args = {"user_id": user.id}
    message = f"{user.name}({user.id})老师的插画更新"

    return watch_args, message


async def parse_following_illusts_args(args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]):
    if len(args) > 1:
        user = await parse_and_get_user(args[1])

        watch_args = {"pixiv_user_id": user.id,
                      "sender_user_id": post_dest.user_id}
        message = f"{user.name}({user.id})用户的关注者插画更新"
    else:
        watch_args = {"pixiv_user_id": 0,
                      "sender_user_id": post_dest.user_id}
        message = "关注者插画更新"

    return watch_args, message


class WatchHandler(SubCommandHandler, subcommand='watch', service=manage_watch_service):

    @classmethod
    def type(cls) -> str:
        return "watch"

    async def parse_args(self, args: Sequence[str]) -> dict:
        if len(args) == 0:
            raise BadRequestError()

        if args[0] == 'fetch':
            if len(args) < 2:
                raise BadRequestError("请指定订阅ID")
            return {"operation": "fetch",
                    "code": args[1]}

        try:
            type = WatchType[args[0]]
            if type == WatchType.user_illusts:
                watch_kwargs, message = await parse_user_illusts_args(args)
            elif type == WatchType.following_illusts:
                watch_kwargs, message = await parse_following_illusts_args(args, self.post_dest)
            else:
                raise KeyError()
        except KeyError as e:
            raise BadRequestError(f"未知订阅类型：{args[0]}") from e

        return {"operation": "add",
                "type": type,
                "watch_kwargs": watch_kwargs,
                "success_message": "成功订阅" + message}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, operation: str, **kwargs):
        if operation == 'fetch':
            ok = await watchman.fetch(kwargs['code'], self.post_dest)
            if ok:
                await self.post_plain_text("拉取完毕")
            else:
                raise BadRequestError("不存在该订阅")
        elif operation == 'add':
            ok = await watchman.add_task(kwargs['type'], kwargs['watch_kwargs'], self.post_dest)
            if ok:
                await self.post_plain_text(kwargs['success_message'])
            else:
                raise BadRequestError("该订阅已存在")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n\n'

        msg += await build_tasks_msg(self.post_dest)
        msg += "\n" \
               f"命令格式：{default_command_start}pixivbot watch <type> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有user_illusts, following_illusts\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               f"示例：{default_command_start}pixivbot watch user_illusts <用户名>\n"
        await self.post_plain_text(message=msg)


class UnwatchHandler(SubCommandHandler, subcommand='unwatch', service=manage_watch_service):
    @classmethod
    def type(cls) -> str:
        return "unwatch"

    async def parse_args(self, args: Sequence[str]) -> dict:
        if len(args) == 0:
            raise BadRequestError()
        return {"code": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, code: str):
        if await watchman.remove_task(self.post_dest, code):
            await self.post_plain_text(message="取消订阅成功")
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_tasks_msg(self.post_dest)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unwatch <id>"
        await self.post_plain_text(message=msg)

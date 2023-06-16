from argparse import Namespace
from io import StringIO

from nonebot.rule import ArgumentParser
from nonebot_plugin_session import Session

from .command import SubCommandHandler
from ..pkg_context import context
from ...model import WatchType
from ...plugin_service import manage_watch_service
from ...service.pixiv_service import PixivService
from ...service.watchman import Watchman
from ...utils.errors import BadRequestError
from ...utils.nonebot import default_command_start

watchman = context.require(Watchman)
pixiv = context.require(PixivService)


async def parse_and_get_user(raw_user: str):
    # try parse
    try:
        user = int(raw_user)
        return await pixiv.get_user(user)
    except ValueError:
        return await pixiv.get_user(raw_user)


async def build_tasks_msg(session: Session):
    tasks = [x async for x in watchman.get_by_subscriber(session)]
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


async def parse_user_illusts_args(args: Namespace):
    if not args.user:
        raise BadRequestError("请指定要订阅的用户")

    user = await parse_and_get_user(args.user)

    watch_args = {"user_id": user.id}
    message = f"成功订阅{user.name}({user.id})老师的插画更新"

    return watch_args, message


async def parse_following_illusts_args(args: Namespace):
    if args.user:
        user = await parse_and_get_user(args.user)

        watch_args = {"pixiv_user_id": user.id}
        message = f"成功订阅{user.name}({user.id})用户的关注者插画更新"
    else:
        watch_args = {"pixiv_user_id": 0}
        message = "成功订阅关注者插画更新"

    return watch_args, message


def use_watch_parser(parser: ArgumentParser):
    subparsers = parser.add_subparsers(title="type", dest="type", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("code")

    user_illusts_parser = subparsers.add_parser("user_illusts")
    user_illusts_parser.add_argument("--user", required=True)

    following_illusts_parser = subparsers.add_parser("following_illusts")
    following_illusts_parser.add_argument("--user")


class WatchHandler(SubCommandHandler, subcommand='watch', service=manage_watch_service,
                   use_subcommand_parser=use_watch_parser):
    @classmethod
    def type(cls) -> str:
        return "watch"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Namespace):
        if not args.type:
            raise BadRequestError()
        elif args.type == 'fetch':
            if not args.code:
                raise BadRequestError("请指定订阅ID")
            ok = await watchman.fetch(args.code, self.session)
            if ok:
                await self.post_plain_text("拉取完毕")
            else:
                raise BadRequestError("不存在该订阅")
        else:
            if args.type == "user_illusts":
                watch_kwargs, success_message = await parse_user_illusts_args(args)
            elif args.type == "following_illusts":
                watch_kwargs, success_message = await parse_following_illusts_args(args)
            else:
                raise BadRequestError()

            ok = await watchman.add_task(WatchType(args.type), watch_kwargs, self.session)
            if ok:
                await self.post_plain_text(success_message)
            else:
                raise BadRequestError("该订阅已存在")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n\n'

        msg += await build_tasks_msg(self.session)
        msg += "\n" \
               f"命令格式：{default_command_start}pixivbot watch <type> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有user_illusts, following_illusts\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               f"示例：{default_command_start}pixivbot watch user_illusts --user <用户名>\n"
        await self.post_plain_text(message=msg)


def use_unwatch_parser(parser: ArgumentParser):
    parser.add_argument("code")


class UnwatchHandler(SubCommandHandler, subcommand='unwatch', service=manage_watch_service,
                     use_subcommand_parser=use_unwatch_parser):
    @classmethod
    def type(cls) -> str:
        return "unwatch"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Namespace):
        if not args.code:
            raise BadRequestError()
        elif args.code != "all":
            ok = await watchman.remove_task(self.session, args.code)
        else:
            await watchman.remove_all_by_subscriber(self.session)
            ok = True

        if ok:
            await self.post_plain_text(message="取消订阅成功")
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_tasks_msg(self.session)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unwatch <id>"
        await self.post_plain_text(message=msg)

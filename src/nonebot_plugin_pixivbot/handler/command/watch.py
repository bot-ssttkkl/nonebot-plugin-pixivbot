from typing import TypeVar, Sequence, Dict, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import GroupAdminInterceptor, \
    AnyPermissionInterceptor, SuperuserInterceptor
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

from .command import CommandHandler, SubCommandHandler
from ...service.pixiv_service import PixivService
from ...service.watchman import Watchman

UID = TypeVar("UID")
GID = TypeVar("GID")


async def parse_and_get_user(raw_user: str):
    pixiv = context.require(PixivService)
    # try parse
    try:
        user = int(raw_user)
        return await pixiv.get_user(user)
    except ValueError:
        return await pixiv.get_user(raw_user)


async def get_tasks_text(identifier: PostIdentifier):
    watchman = context.require(Watchman)
    tasks = [t async for t in watchman.get_by_subscriber(identifier)]
    msg = "当前订阅：\n"
    if len(tasks) > 0:
        for t in tasks:
            args_text = " ".join(map(lambda k: f'{k}={t.args[k]}', t.args))
            msg += f'{t.type} {args_text}'
    else:
        msg += '无\n'
    return msg


@context.inject
@context.require(CommandHandler).sub_command("watch")
class WatchHandler(SubCommandHandler):
    watchman: Watchman
    pixiv: PixivService

    def __init__(self):
        super().__init__()
        self.add_interceptor(AnyPermissionInterceptor(
            context.require(SuperuserInterceptor),
            context.require(GroupAdminInterceptor)
        ))

    @classmethod
    def type(cls) -> str:
        return "watch"

    def enabled(self) -> bool:
        return True

    async def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[UID, GID]) -> dict:
        if len(args) == 0:
            raise BadRequestError()

        type = args[0]

        if type == "user_illusts":
            if len(args) < 2:
                raise BadRequestError()

            user = await parse_and_get_user(args[1])
            watch_args = {"user_id": user.id}
            success_message = f"成功订阅{user.name}({user.id})老师的更新"
        else:
            raise BadRequestError("不支持该类型")

        return {"type": args[0], "args": watch_args, "success_message": success_message}

    async def actual_handle(self, *, type: str,
                            args: Dict[str, Any],
                            success_message: str,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.watchman.watch(type, args, post_dest)
        await self.post_plain_text(success_message, post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        if err.message:
            await self.post_plain_text(err.message, post_dest)
        else:
            msg = await get_tasks_text(post_dest.identifier)
            msg += "\n"
            msg += "命令格式：/pixivbot watch <type> <..args>\n"
            msg += "示例：/pixivbot watch user_illusts <用户名>\n"
            await self.post_plain_text(message=msg, post_dest=post_dest)


@context.inject
@context.require(CommandHandler).sub_command("unwatch")
class UnwatchHandler(SubCommandHandler):
    watchman: Watchman
    pixiv: PixivService

    def __init__(self):
        super().__init__()
        self.add_interceptor(AnyPermissionInterceptor(
            context.require(SuperuserInterceptor),
            context.require(GroupAdminInterceptor)
        ))

    @classmethod
    def type(cls) -> str:
        return "unwatch"

    def enabled(self) -> bool:
        return True

    async def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[UID, GID]) -> dict:
        if len(args) == 0:
            raise BadRequestError()

        type = args[0]

        if type == "user_illusts":
            user = await parse_and_get_user(args[1])
            watch_args = {"user_id": user.id}
        else:
            raise BadRequestError("不支持该类型")

        return {"type": args[0], "args": watch_args}

    async def actual_handle(self, *, type: str,
                            args: Dict[str, Any],
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.watchman.unwatch(type, args, post_dest)
        await self.post_plain_text(message="取消订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        if err.message:
            await self.post_plain_text(err.message, post_dest)
        else:
            msg = await get_tasks_text(post_dest.identifier)
            msg += "\n"
            msg += "命令格式：/pixivbot unwatch <type> <..args>\n"
            msg += "示例：/pixivbot unwatch user_illusts <用户名>\n"
            await self.post_plain_text(message=msg, post_dest=post_dest)

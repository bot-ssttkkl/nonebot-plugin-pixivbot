from typing import TypeVar, Sequence, Dict, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import GroupAdminInterceptor, \
    AnyPermissionInterceptor, SuperuserInterceptor
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from nonebot_plugin_pixivbot.service.watchman import Watchman
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import CommandHandler, SubCommandHandler
from ...service.pixiv_account_binder import PixivAccountBinder

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


async def build_tasks_msg(identifier: PostIdentifier):
    watchman = context.require(Watchman)
    tasks = await watchman.get_by_subscriber(identifier)
    msg = "当前订阅：\n"
    if len(tasks) > 0:
        for t in tasks:
            args_text = " ".join(map(lambda k: f'{k}={t.kwargs[k]}', t.kwargs))
            msg += f'{t.type.name} {args_text}\n'
    else:
        msg += '无\n'
    return msg


@context.inject
@context.require(CommandHandler).sub_command("watch")
class WatchHandler(SubCommandHandler):
    watchman: Watchman
    binder: PixivAccountBinder

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

        try:
            type = WatchType[args[0]]

            if type == WatchType.user_illusts:
                if len(args) < 2:
                    raise BadRequestError()

                user = await parse_and_get_user(args[1])
                watch_args = {"user_id": user.id}
                success_message = f"成功订阅{user.name}({user.id})老师的插画更新"
            elif type == WatchType.following_illusts:
                user_id = await self.binder.get_binding(post_dest.adapter, post_dest.user_id)
                if not user_id:
                    raise BadRequestError("未绑定Pixiv账号")
                watch_args = {"user_id": user_id}
                success_message = f"成功订阅关注者插画更新"
            else:
                raise KeyError()
        except KeyError as e:
            raise BadRequestError(f"未知订阅类型：{args[0]}") from e

        return {"type": type, "args": watch_args, "success_message": success_message}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, type: WatchType,
                            args: Dict[str, Any],
                            success_message: str,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.watchman.watch(type, args, post_dest)
        await self.post_plain_text(success_message, post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_tasks_msg(post_dest.identifier)
        msg += "\n"
        msg += "命令格式：/pixivbot watch <type> <..args>\n"
        msg += "示例：/pixivbot watch user_illusts <用户名>\n"
        await self.post_plain_text(message=msg, post_dest=post_dest)


@context.inject
@context.require(CommandHandler).sub_command("unwatch")
class UnwatchHandler(SubCommandHandler):
    watchman: Watchman
    binder: PixivAccountBinder

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

        try:
            type = WatchType[args[0]]

            if type == WatchType.user_illusts:
                if len(args) < 2:
                    raise BadRequestError()

                user = await parse_and_get_user(args[1])
                watch_args = {"user_id": user.id}
            elif type == WatchType.following_illusts:
                user_id = await self.binder.get_binding(post_dest.adapter, post_dest.user_id)
                if not user_id:
                    raise BadRequestError("未绑定Pixiv账号")
                watch_args = {"user_id": user_id}
            else:
                raise KeyError()
        except KeyError as e:
            raise BadRequestError(f"未知订阅类型：{args[0]}") from e

        return {"type": type, "kwargs": watch_args}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, type: WatchType,
                            kwargs: Dict[str, Any],
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        if await self.watchman.unwatch(type, kwargs, post_dest.identifier):
            await self.post_plain_text(message="取消订阅成功", post_dest=post_dest)
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_tasks_msg(post_dest.identifier)
        msg += "\n"
        msg += "命令格式：/pixivbot unwatch <type> <..args>\n"
        msg += "示例：/pixivbot unwatch user_illusts <用户名>\n"
        await self.post_plain_text(message=msg, post_dest=post_dest)

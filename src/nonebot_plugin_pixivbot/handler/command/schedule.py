from typing import Sequence

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import GroupAdminInterceptor, \
    AnyPermissionInterceptor, SuperuserInterceptor
from nonebot_plugin_pixivbot.model import PostIdentifier, ScheduleType
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import CommandHandler, SubCommandHandler
from ..pkg_context import context
from ... import default_command_start


async def build_subscriptions_msg(subscriber: PostIdentifier[T_UID, T_GID]):
    scheduler = context.require(Scheduler)
    subscription = [x async for x in scheduler.get_by_subscriber(subscriber)]
    msg = "当前订阅：\n"
    if len(subscription) > 0:
        for x in subscription:
            args = list(filter(lambda kv: kv[1], x.kwargs.items()))
            if len(args) != 0:
                args_text = ", ".join(map(lambda kv: f'{kv[0]}={kv[1]}', args))
                args_text = f"({args_text})"
            else:
                args_text = ""
            schedule_text = f'{str(x.schedule[0]).zfill(2)}:{str(x.schedule[1]).zfill(2)}' \
                            f'+{str(x.schedule[2]).zfill(2)}:{str(x.schedule[3]).zfill(2)}*x'
            msg += f'[{x.code}] {x.type.name} {schedule_text} {args_text}\n'
    else:
        msg += '无\n'
    return msg


@context.inject
@context.require(CommandHandler).sub_command("schedule")
class ScheduleHandler(SubCommandHandler):
    scheduler = Inject(Scheduler)

    def __init__(self):
        super().__init__()
        self.add_interceptor(AnyPermissionInterceptor(
            context.require(SuperuserInterceptor),
            context.require(GroupAdminInterceptor)
        ))

    @classmethod
    def type(cls) -> str:
        return "schedule"

    def enabled(self) -> bool:
        return True

    def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[T_UID, T_GID]) -> dict:
        if len(args) < 2:
            raise BadRequestError()
        try:
            return {"type": ScheduleType(args[0]),
                    "schedule": args[1],
                    "args": args[2:]}
        except ValueError as e:
            raise BadRequestError(f"未知订阅类型：{args[0]}") from e

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, type: ScheduleType,
                            schedule: str,
                            args: Sequence[str],
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False, **kwargs):
        await self.scheduler.schedule(type, schedule, args, post_dest)
        await self.post_plain_text(message="订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[T_UID, T_GID],
                                        silently: bool = False):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(post_dest.identifier)
        msg += "\n" \
               f"命令格式：{default_command_start}pixivbot schedule <type> <schedule> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
               "random_user_illust, ranking\n" \
               "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送）\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               f"示例：{default_command_start}pixivbot schedule ranking 06:00*x day 1-5"
        await self.post_plain_text(message=msg, post_dest=post_dest)


@context.inject
@context.require(CommandHandler).sub_command("unschedule")
class UnscheduleHandler(SubCommandHandler):
    scheduler = Inject(Scheduler)

    def __init__(self):
        super().__init__()
        self.add_interceptor(AnyPermissionInterceptor(
            context.require(SuperuserInterceptor),
            context.require(GroupAdminInterceptor)
        ))

    @classmethod
    def type(cls) -> str:
        return "unschedule"

    def enabled(self) -> bool:
        return True

    def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[T_UID, T_GID]) -> dict:
        if len(args) == 0:
            raise BadRequestError()
        return {"code": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, code: int,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        if await self.scheduler.unschedule(post_dest.identifier, code):
            await self.post_plain_text(message="取消订阅成功", post_dest=post_dest)
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[T_UID, T_GID],
                                        silently: bool = False):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(post_dest.identifier)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unschedule <id>"
        await self.post_plain_text(message=msg, post_dest=post_dest)

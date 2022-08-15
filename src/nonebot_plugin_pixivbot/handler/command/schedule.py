from typing import List, TypeVar, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import GroupAdminInterceptor, \
    AnyPermissionInterceptor, SuperuserInterceptor
from nonebot_plugin_pixivbot.model import PostIdentifier, ScheduleType
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import CommandHandler, SubCommandHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


async def build_subscriptions_msg(subscriber: PostIdentifier[UID, GID]):
    scheduler = context.require(Scheduler)
    subscription = await scheduler.get_by_subscriber(subscriber)
    msg = "当前订阅：\n"
    if len(subscription) > 0:
        for x in subscription:
            msg += f'{x.type.name} ' \
                   f'{str(x.schedule[0]).zfill(2)}:{str(x.schedule[1]).zfill(2)}' \
                   f'+{str(x.schedule[2]).zfill(2)}:{str(x.schedule[3]).zfill(2)}*x\n'
    else:
        msg += '无\n'
    return msg


@context.inject
@context.require(CommandHandler).sub_command("schedule")
class ScheduleHandler(SubCommandHandler):
    scheduler: Scheduler

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

    def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[UID, GID]) -> dict:
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
                            args: List,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.scheduler.schedule(type, schedule, args, post_dest=post_dest)
        await self.post_plain_text(message="订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(post_dest.identifier)
        msg += "\n" \
               "命令格式：/pixivbot schedule <type> <schedule> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
               "random_user_illust, ranking\n" \
               "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送）\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               "示例：/pixivbot schedule ranking 06:00*x day 1-5"
        await self.post_plain_text(message=msg, post_dest=post_dest)


@context.inject
@context.require(CommandHandler).sub_command("unschedule")
class UnscheduleHandler(SubCommandHandler):
    scheduler: Scheduler

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

    def parse_args(self, args: Sequence[str], post_dest: PostIdentifier[UID, GID]) -> dict:
        if len(args) == 0:
            raise BadRequestError()
        try:
            return {"type": ScheduleType(args[0])}
        except ValueError as e:
            raise BadRequestError(f"未知订阅类型：{args[0]}") from e

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, type: ScheduleType,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        if await self.scheduler.unschedule(type, post_dest.identifier):
            await self.post_plain_text(message="取消订阅成功", post_dest=post_dest)
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(post_dest.identifier)
        msg += "\n"
        msg += "命令格式：/pixivbot unschedule <type>"
        await self.post_plain_text(message=msg, post_dest=post_dest)

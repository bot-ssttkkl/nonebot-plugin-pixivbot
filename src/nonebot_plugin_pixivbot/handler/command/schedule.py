from typing import List, TypeVar, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import GroupAdminInterceptor, \
    AnyPermissionInterceptor, SuperuserInterceptor
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import CommandHandler, SubCommandHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


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
        return {"type": args[0],
                "schedule": args[1],
                "args": args[2:]}

    async def actual_handle(self, *, type: str,
                            schedule: str,
                            args: List,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.scheduler.schedule(type, schedule, args, post_dest=post_dest)
        await self.post_plain_text(message="订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        subscription = await self.scheduler.all_subscription(post_dest.identifier)
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x.type} {str(x.schedule[0]).zfill(2)}:{str(x.schedule[1]).zfill(2)}+{str(x.schedule[2]).zfill(2)}:{str(x.schedule[3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        msg += "命令格式：/pixivbot schedule <type> <schedule> <..args>\n"
        msg += "示例：/pixivbot schedule ranking 06:00*x day 1-5\n"
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
        return {"type": args[0]}

    async def actual_handle(self, *, type: str,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        await self.scheduler.unschedule(type, post_dest.identifier)
        await self.post_plain_text(message="取消订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, *, post_dest: PostDestination[UID, GID],
                                        silently: bool = False,
                                        err: BadRequestError):
        subscription = await self.scheduler.all_subscription(post_dest.identifier)
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x.type} {str(x.schedule[0]).zfill(2)}:{str(x.schedule[1]).zfill(2)}+{str(x.schedule[2]).zfill(2)}:{str(x.schedule[3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        msg += "命令格式：/pixivbot unschedule <type>"
        await self.post_plain_text(message=msg, post_dest=post_dest)

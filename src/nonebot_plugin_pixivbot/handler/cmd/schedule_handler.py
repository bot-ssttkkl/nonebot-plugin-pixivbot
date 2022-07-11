from typing import List, TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.cmd.command_handler import CommandHandler, SubCommandHandler
from nonebot_plugin_pixivbot.postman import PostDestination, PostIdentifier
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.require(CommandHandler).sub_command("schedule")
class ScheduleHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    scheduler = context.require(Scheduler)

    @classmethod
    def type(cls) -> str:
        return "schedule"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {"type": args[0],
                "schedule": args[1],
                "args": args[2:]}

    async def actual_handle(self, *, type: str,
                            schedule: str,
                            args: List,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        await self.scheduler.schedule(type, schedule, args, bot=post_dest.bot, identifier=post_dest.identifier)
        await self.postman.send_plain_text(message="订阅成功", post_dest=post_dest)

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID, B, M]):
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
        await self.postman.send_plain_text(message=msg, post_dest=post_dest)


@context.require(CommandHandler).sub_command("unschedule")
class UnscheduleHandler(SubCommandHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    scheduler = context.require(Scheduler)

    @classmethod
    def type(cls) -> str:
        return "unschedule"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {"type": args[0]}

    async def actual_handle(self, *, type: str,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        await self.scheduler.unschedule(type, post_dest.identifier)
        await self.postman.send_plain_text(message="取消订阅成功", post_dest=post_dest)

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID, B, M]):
        subscription = await self.scheduler.all_subscription(post_dest.identifier)
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x.type} {str(x.schedule[0]).zfill(2)}:{str(x.schedule[1]).zfill(2)}+{str(x.schedule[2]).zfill(2)}:{str(x.schedule[3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        msg += "命令格式：/pixivbot unschedule <type>"
        await self.postman.send_plain_text(message=msg, post_dest=post_dest)

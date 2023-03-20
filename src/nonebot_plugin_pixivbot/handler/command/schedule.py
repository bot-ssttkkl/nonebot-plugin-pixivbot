from io import StringIO
from typing import Sequence

from nonebot_plugin_pixivbot.model import ScheduleType
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import manage_schedule_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.nonebot import default_command_start
from .subcommand import SubCommandHandler
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context

scheduler = context.require(Scheduler)


async def build_subscriptions_msg(post_dest: PostDestination[T_UID, T_GID]):
    scheduler = context.require(Scheduler)
    subscription = [x async for x in scheduler.get_by_subscriber(post_dest)]
    with StringIO() as sio:
        sio.write("当前订阅：\n")
        if len(subscription) > 0:
            for sub in subscription:
                sio.write(f'[{sub.code}] {sub.type.name} {sub.schedule_text}')
                args_text = sub.args_text
                if args_text:
                    sio.write(f' ({args_text})')
                sio.write('\n')
        else:
            sio.write('无\n')
        return sio.getvalue()


class ScheduleHandler(SubCommandHandler, subcommand='schedule',
                      interceptors=[ServiceInterceptor(manage_schedule_service)]):
    @classmethod
    def type(cls) -> str:
        return "schedule"

    async def parse_args(self, args: Sequence[str]) -> dict:
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
                            args: Sequence[str]):
        await scheduler.add_task(type, schedule, args, self.post_dest)
        await self.post_plain_text(message="订阅成功")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(self.post_dest)
        msg += "\n" \
               f"命令格式：{default_command_start}pixivbot schedule <type> <schedule> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
               "random_user_illust, ranking\n" \
               "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送）\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               f"示例：{default_command_start}pixivbot schedule ranking 06:00*x day 1-5"
        await self.post_plain_text(message=msg)


class UnscheduleHandler(SubCommandHandler, subcommand='unschedule',
                        interceptors=[ServiceInterceptor(manage_schedule_service)]):
    @classmethod
    def type(cls) -> str:
        return "unschedule"

    async def parse_args(self, args: Sequence[str]) -> dict:
        if len(args) == 0:
            raise BadRequestError()
        return {"code": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, code: str):
        if await scheduler.remove_task(self.post_dest, code):
            await self.post_plain_text(message="取消订阅成功")
        else:
            raise BadRequestError("取消订阅失败，不存在该订阅")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(self.post_dest)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unschedule <id>"
        await self.post_plain_text(message=msg)

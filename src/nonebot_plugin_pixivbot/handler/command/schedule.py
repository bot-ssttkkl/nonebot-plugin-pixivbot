from io import StringIO
from typing import Sequence

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import PostIdentifier, ScheduleType
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import manage_schedule_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.scheduler import Scheduler
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.nonebot import default_command_start
from .command import SubCommandHandler
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context


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


@context.inject
@context.register_singleton()
class ScheduleHandler(SubCommandHandler, subcommand='schedule'):
    scheduler: Scheduler = Inject(Scheduler)

    def __init__(self):
        super().__init__()
        self.add_interceptor(ServiceInterceptor(manage_schedule_service))

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
        await self.scheduler.add_task(type, schedule, args, post_dest)
        await self.post_plain_text(message="订阅成功", post_dest=post_dest)

    async def actual_handle_bad_request(self, err: BadRequestError,
                                        *, post_dest: PostDestination[T_UID, T_GID],
                                        silently: bool = False):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(post_dest)
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
@context.register_singleton()
class UnscheduleHandler(SubCommandHandler, subcommand='unschedule'):
    scheduler: Scheduler = Inject(Scheduler)

    def __init__(self):
        super().__init__()
        self.add_interceptor(ServiceInterceptor(manage_schedule_service))

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
    async def actual_handle(self, *, code: str,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        if await self.scheduler.remove_task(post_dest, code):
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

        msg += await build_subscriptions_msg(post_dest)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unschedule <id>"
        await self.post_plain_text(message=msg, post_dest=post_dest)

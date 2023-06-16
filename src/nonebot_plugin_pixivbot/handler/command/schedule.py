from argparse import Namespace
from io import StringIO

from nonebot.rule import ArgumentParser
from nonebot_plugin_session import Session

from .command import SubCommandHandler
from ..pkg_context import context
from ...model import ScheduleType
from ...plugin_service import manage_schedule_service
from ...service.scheduler import Scheduler
from ...utils.errors import BadRequestError
from ...utils.nonebot import default_command_start

scheduler = context.require(Scheduler)


async def build_subscriptions_msg(session: Session):
    scheduler = context.require(Scheduler)
    subscription = [x async for x in scheduler.get_by_subscriber(session)]
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


def use_schedule_parser(parser: ArgumentParser):
    subparsers = parser.add_subparsers(title="type", dest="type", required=True)

    random_bookmark_parser = subparsers.add_parser("random_bookmark")
    random_bookmark_parser.add_argument("schedule")
    random_bookmark_parser.add_argument("--user", required=False)

    random_recommended_illust_parser = subparsers.add_parser("random_recommended_illust")
    random_recommended_illust_parser.add_argument("schedule")

    random_illust_parser = subparsers.add_parser("random_illust")
    random_illust_parser.add_argument("schedule")
    random_illust_parser.add_argument("--word", required=True)

    random_user_illust_parser = subparsers.add_parser("random_user_illust")
    random_user_illust_parser.add_argument("schedule")
    random_user_illust_parser.add_argument("--user", required=True)

    ranking_parser = subparsers.add_parser("ranking")
    ranking_parser.add_argument("schedule")
    ranking_parser.add_argument("--mode", required=False)
    ranking_parser.add_argument("--range", required=False)


class ScheduleHandler(SubCommandHandler, subcommand='schedule', service=manage_schedule_service,
                      use_subcommand_parser=use_schedule_parser):
    @classmethod
    def type(cls) -> str:
        return "schedule"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Namespace):
        task_args = []
        if args.type == "random_bookmark":
            task_args.append(args.user)
        elif args.type == "random_illust":
            task_args.append(args.word)
        elif args.type == "random_user_illust":
            task_args.append(args.user)
        elif args.type == "ranking":
            task_args.append(args.mode)
            task_args.append(args.range)

        while len(task_args) > 0 and task_args[-1] is None:
            task_args.pop()

        await scheduler.add_task(ScheduleType(args.type), args.schedule, task_args, self.session)
        await self.post_plain_text(message="订阅成功")

    async def actual_handle_bad_request(self, err: BadRequestError):
        msg = ""
        if err.message:
            msg += err.message
            msg += '\n'

        msg += await build_subscriptions_msg(self.session)
        msg += "\n" \
               f"命令格式：{default_command_start}pixivbot schedule <type> <schedule> [..args]\n" \
               "参数：\n" \
               "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
               "random_user_illust, ranking\n" \
               "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送），或者使用cron表达式\n" \
               "  [...args]：根据<type>不同需要提供不同的参数\n" \
               f"示例：{default_command_start}pixivbot schedule ranking 06:00*x --mode day --range 1-5"
        await self.post_plain_text(message=msg)


def use_unschedule_parser(parser: ArgumentParser):
    parser.add_argument("code", default="")


class UnscheduleHandler(SubCommandHandler, subcommand='unschedule', service=manage_schedule_service,
                        use_subcommand_parser=use_unschedule_parser):
    @classmethod
    def type(cls) -> str:
        return "unschedule"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Namespace):
        if args.code != "all":
            ok = await scheduler.remove_task(self.session, args.code)
        else:
            await scheduler.remove_all_by_subscriber(self.session)
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

        msg += await build_subscriptions_msg(self.session)
        msg += "\n"
        msg += f"命令格式：{default_command_start}pixivbot unschedule <id>"
        await self.post_plain_text(message=msg)

from nonebot import on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..config import Config
from ..controller import Scheduler
from ..data_source import PixivBindings, PixivDataSource
from .pkg_context import context
from .catch_error import catch_error

conf = context.require(Config)
pixiv_bindings = context.require(PixivBindings)
pixiv_data_source = context.require(PixivDataSource)
scheduler = context.require(Scheduler)

_help_text = """常规语句：
- 看看榜：查看pixiv榜单
- 看看榜21-25：查看pixiv榜单的第21到第25名
- 看看榜50：查看pixiv榜单的第50名
- 来张图：从推荐插画随机抽选一张插画
- 来张初音ミク图：搜索关键字初音ミク，从搜索结果随机抽选一张插画
- 来张森倉円老师的图：搜索画师森倉円，从该画师的插画列表里随机抽选一张插画
- 看看图114514：查看id为114514的插画
- 来张私家车：从书签中随机抽选一张插画
- 还要：重复上一次请求
- 不够色：获取上一张插画的相关推荐

命令语句：
- /pixivbot help：查看本帮助
- /pixivbot bind：绑定Pixiv账号

更多功能：参见https://github.com/ssttkkl/PixivBot
"""


# def _get_user_and_group_id(event: Event):
#     d = {}
#     if "group_id" in event.__fields__ and event.group_id:
#         d["group_id"] = event.group_id
#     if "user_id" in event.__fields__ and event.user_id:
#         d["user_id"] = event.user_id
#     return d


def _get_user_or_group_id(event: Event):
    if "group_id" in event.__fields__ and event.group_id:
        return {"group_id": event.group_id}
    elif "user_id" in event.__fields__ and event.user_id:
        return {"user_id": event.user_id}
    else:
        return {}


super_command = on_command("pixivbot", priority=5)


@super_command.handle()
async def handle_super_command(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    state["args"] = str(event.get_message()).strip().split()[1:]
    # 未跟参数或参数为help时，输出帮助信息
    if len(state["args"]) == 0 or state["args"][0] == "help":
        await matcher.finish(_help_text)


@super_command.handle()
@catch_error
async def handle_bind(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    args = state["args"]
    if len(args) == 0 or args[0] != "bind":
        return

    # sample: /pixivbot bind 114514
    if "user_id" in event.__fields__ and event.user_id:
        qq_id = event.user_id
    else:
        raise AttributeError("user_id")

    if len(args) < 2:
        pixiv_user_id = await pixiv_bindings.get_binding(qq_id)
        if pixiv_user_id is not None:
            msg = f"当前绑定账号：{pixiv_user_id}\n"
        else:
            msg = "当前未绑定Pixiv账号\n"
        msg += "命令格式：/pixivbot bind <pixiv_user_id>"
        await matcher.send(msg)
    else:
        pixiv_user_id = int(state["args"][1])
        await pixiv_bindings.bind(qq_id, pixiv_user_id)
        await matcher.send("Pixiv账号绑定成功")


@super_command.handle()
@catch_error
async def handle_unbind(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    args = state["args"]
    if len(args) == 0 or state["args"][0] != "unbind":
        return

    # sample: /pixivbot unbind
    if "user_id" in event.__fields__ and event.user_id:
        qq_id = event.user_id
    else:
        raise AttributeError("user_id")

    await pixiv_bindings.unbind(qq_id)
    await matcher.send("Pixiv账号解绑成功")


@super_command.handle()
@catch_error
async def handle_schedule(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    args: list = state["args"]
    if len(args) == 0 or state["args"][0] != "schedule":
        return
    if isinstance(event, GroupMessageEvent) and not (event.sender.role == "admin" or event.sender.role == "owner" or await SUPERUSER(bot, event)):
        await matcher.send("只有群主/管理员/超级用户可以调用该命令")
        return

    # sample: /pixivbot schedule random_bookmark 00:00+00:30*x <args> <kwargs>
    if len(args) < 3:
        subscription = await scheduler.all_subscription(**_get_user_or_group_id(event))
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x["type"]} {str(x["schedule"][0]).zfill(2)}:{str(x["schedule"][1]).zfill(2)}+{str(x["schedule"][2]).zfill(2)}:{str(x["schedule"][3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        msg += "命令格式：/pixivbot schedule <type> <schedule>\n"
        msg += "type可选值：ranking, random_bookmark, random_recommended_illust\n"
        msg += "schedule可选格式：12:00, 01:00*x, 00:10+00:30*x\n"
        await matcher.send(msg)
    else:
        sch_args = args[3:]
        # if args[1] == "random_bookmark":
        #     sch_args.insert(0, event.user_id)

        await scheduler.schedule(args[1], args[2], sch_args, bot=bot, **_get_user_or_group_id(event))
        await matcher.send("订阅成功")


@super_command.handle()
@catch_error
async def handle_unschedule(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    args = state["args"]
    if len(args) == 0 or state["args"][0] != "unschedule":
        return
    if isinstance(event, GroupMessageEvent) and not (event.sender.role == "admin" or event.sender.role == "owner" or await SUPERUSER(bot, event)):
        await matcher.send("只有群主/管理员/超级用户可以调用该命令")
        return

    # sample: /pixivbot unschedule random_bookmark
    if len(args) < 2:
        subscription = await scheduler.all_subscription(**_get_user_or_group_id(event))
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x["type"]} {str(x["schedule"][0]).zfill(2)}:{str(x["schedule"][1]).zfill(2)}+{str(x["schedule"][2]).zfill(2)}:{str(x["schedule"][3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        await matcher.send("命令格式：/pixivbot unschedule <type>")
    else:
        await scheduler.unschedule(args[1], **_get_user_or_group_id(event))
        await matcher.send("取消订阅成功")


@super_command.handle()
@catch_error
async def handle_invalidate_cache(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    args = state["args"]
    if len(args) == 0 or state["args"][0] != "invalidate_cache":
        return
    if not await SUPERUSER(bot, event):
        await matcher.send("只有超级用户可以调用该命令")
        return

    await pixiv_data_source.invalidate_cache()
    await matcher.send("ok")

from nonebot import on_command
from nonebot.adapters.cqhttp import Bot, Event, GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .scheduled_distributor import sch_distributor


def _get_user_or_group_id(event: Event):
    if isinstance(event, GroupMessageEvent):
        return {"group_id": event.group_id}
    else:
        return {"user_id": event.get_user_id()}


superuser_command = on_command("pixivbot", rule=to_me(), permission=SUPERUSER, priority=5)


@superuser_command.handle()
async def handle_superuser_command(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    state["args"] = str(event.get_message()).strip().split()
    if len(state["args"]) < 1:
        await matcher.finish("请指定命令类型")


@superuser_command.handle()
async def handle_subscribe(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    if state["args"][0] != "subscribe":
        return

    # sample: /pixivbot subscribe random_bookmark 00:00+00:30*x
    if len(state["args"]) < 3:
        subscription = await sch_distributor.all_subscription(**_get_user_or_group_id(event))
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x["type"]} {x["schedule"][0]}:{x["schedule"][1]}+{x["schedule"][2]}:{x["schedule"][3]}*x\n'
        else:
            msg += '无'
        await matcher.send(msg.strip('\n'))
        await matcher.finish("sample: /pixivbot subscribe random_bookmark 00:30*x\n"
                             "        /pixivbot subscribe ranking 12:00\n"
                             "        /pixivbot subscribe random_recommended_illust 00:10+00:30*x")
        return
    await sch_distributor.subscribe(state["args"][1], state["args"][2], bot=bot,
                                    **_get_user_or_group_id(event))
    await matcher.finish("ok")


@superuser_command.handle()
async def handle_unsubscribe(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    if state["args"][0] != "unsubscribe":
        return

    # sample: /pixivbot unsubscribe random_bookmark
    if len(state["args"]) < 2:
        await matcher.finish("sample: /pixivbot unsubscribe random_bookmark")
        return

    await sch_distributor.unsubscribe(state["args"][1], **_get_user_or_group_id(event))
    await matcher.finish("ok")

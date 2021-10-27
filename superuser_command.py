from nonebot import on_command, logger
from nonebot.adapters.cqhttp import Bot, Event
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .scheduled_distributor import sch_distributor


_help_text = """触发语句：
- 看看榜：查看pixiv榜单
- 看看榜21-25：查看pixiv榜单的第21到第25名
- 看看榜50：查看pixiv榜单的第50名
- 来张图：从推荐插画随机抽选一张插画
- 来张初音ミク图：搜索关键字初音ミク，从搜索结果随机抽选一张插画
- 来张森倉円老师的图：搜索画师森倉円，从该画师的插画列表里随机抽选一张插画
- 看看图114514：查看id为114514的插画
- 来张私家车：从书签中随机抽选一张插画

更多功能：参见https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""


def _get_user_or_group_id(event: Event):
    if "group_id" in event.__fields__ and event.group_id:
        return {"group_id": event.group_id}
    elif "user_id" in event.__fields__ and event.user_id:
        return {"user_id": event.user_id}
    else:
        return {}


superuser_command = on_command("pixivbot", rule=to_me(), priority=5)


@superuser_command.handle()
async def handle_superuser_command(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    state["args"] = str(event.get_message()).strip().split()
    if len(state["args"]) == 0 or state["args"][0] == "help":
        await matcher.finish(_help_text)


@superuser_command.handle()
async def handle_subscribe(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    if state["args"][0] != "subscribe":
        return
    if not await SUPERUSER(bot, event):
        await matcher.finish("只有超级用户可以调用该命令")

    # sample: /pixivbot subscribe random_bookmark 00:00+00:30*x
    if len(state["args"]) < 3:
        subscription = await sch_distributor.all_subscription(**_get_user_or_group_id(event))
        msg = "当前订阅：\n"
        if len(subscription) > 0:
            for x in subscription:
                msg += f'{x["type"]} {str(x["schedule"][0]).zfill(2)}:{str(x["schedule"][1]).zfill(2)}+{str(x["schedule"][2]).zfill(2)}:{str(x["schedule"][3]).zfill(2)}*x\n'
        else:
            msg += '无\n'
        msg += "\n"
        msg += "sample: /pixivbot subscribe random_bookmark 00:30*x\n"
        msg += "        /pixivbot subscribe ranking 12:00\n"
        msg += "        /pixivbot subscribe random_recommended_illust 00:10+00:30*x"
        await matcher.finish(msg)
        return

    try:
        await sch_distributor.subscribe(state["args"][1], state["args"][2], bot=bot,
                                        **_get_user_or_group_id(event))
        await matcher.finish("ok")
    except Exception as e:
        logger.exception(e)
        await matcher.finish(str(e))


@superuser_command.handle()
async def handle_unsubscribe(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    if state["args"][0] != "unsubscribe":
        return
    if not await SUPERUSER(bot, event):
        await matcher.finish("只有超级用户可以调用该命令")

    # sample: /pixivbot unsubscribe random_bookmark
    if len(state["args"]) < 2:
        await matcher.finish("sample: /pixivbot unsubscribe random_bookmark")
        return

    try:
        await sch_distributor.unsubscribe(state["args"][1], **_get_user_or_group_id(event))
        await matcher.finish("ok")
    except Exception as e:
        logger.exception(e)
        await matcher.finish(str(e))

# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..data_source import data_source
from ..msg_maker import make_illusts_msg
from ..query_error import QueryError

ranking_query = on_regex(r"看看(日|周|月|男性|女性|原创|新人|漫画)?榜\s*(([1-9][0-9]*)[-~]([1-9][0-9]*))?",
                         rule=to_me(), priority=4, block=True)


@ranking_query.handle()
async def handle_ranking_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        mode = state["_matched_groups"][0]
        start = state["_matched_groups"][2]
        end = state["_matched_groups"][3]

        if mode is None:
            mode = "day"
        elif mode == "日":
            mode = "day"
        elif mode == "周":
            mode = "week"
        elif mode == "月":
            mode = "month"
        elif mode == "男性":
            mode = "day_male"
        elif mode == "女性":
            mode = "day_female"
        elif mode == "原创":
            mode = "week_original"
        elif mode == "新人":
            mode = "week_rookie"
        elif mode == "漫画":
            mode = "day_manga"

        if start is None:
            start = 1
        else:
            start = int(start)

        if end is None:
            end = start + 2
        else:
            end = int(end)

        if end - start + 1 > 5:
            await matcher.send("仅支持一次查询5张以下插画")
        elif start > end:
            await matcher.send("范围不合法")
        elif end > 150:
            await matcher.send('仅支持查询150名以内插画')
        else:
            illusts = await data_source.illust_ranking(mode)
            msg = await make_illusts_msg(illusts[start - 1:end], start)
            await matcher.send(msg)
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except Exception as e:
        logger.exception(e)

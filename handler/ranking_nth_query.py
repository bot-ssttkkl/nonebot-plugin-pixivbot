# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..data_source import data_source
from ..msg_maker import make_illust_msg
from ..query_error import QueryError
from ..utils import decode_chinese_integer, decode_integer

ranking_nth_query = on_regex(r"看看(日|周|月|男性|女性|原创|新人)?榜第?\s*([1-9][0-9]*|[零一两二三四五六七八九十百千万亿]+)", rule=to_me(), priority=5)


@ranking_nth_query.handle()
async def handle_ranking_nth_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        mode = state["_matched_groups"][0]
        num = state["_matched_groups"][1]

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

        try:
            num = decode_integer(num)
        except ValueError:
            await matcher.send(f"{num}不是合法的数字")

        if num > 150:
            await matcher.send('仅支持查询150名以内插画')
        else:
            illusts = await data_source.illust_ranking(mode)
            msg = await make_illust_msg(illusts[num - 1])
            await matcher.send(msg)
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except Exception as e:
        logger.exception(e)

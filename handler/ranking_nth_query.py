# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..config import conf
from ..data_source import data_source
from ..msg_maker import make_illust_msg
from ..errors import QueryError, NoReplyError
from ..utils import decode_integer

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

        if num > conf.pixiv_ranking_fetch_item:
            await matcher.send(f'仅支持查询{conf.pixiv_ranking_fetch_item}名以内的插画')
        else:
            illusts = await data_source.illust_ranking(mode, conf.pixiv_ranking_fetch_item,
                                                       block_tags=conf.pixiv_block_tags)
            msg = await make_illust_msg(illusts[num - 1])
            await matcher.send(msg)
    except NoReplyError:
        pass
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except TimeoutError as e:
        await matcher.send("下载超时")
        logger.warning(e)
    except Exception as e:
        logger.exception(e)

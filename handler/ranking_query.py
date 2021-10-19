# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..config import conf
from ..data_source import data_source
from ..errors import QueryError, NoReplyError
from ..msg_maker import make_illusts_msg

if conf.pixiv_ranking_query_enabled:
    ranking_query = on_regex(r"看看(日|周|月|男性|女性|原创|新人|漫画)?榜\s*(([1-9][0-9]*)[-~]([1-9][0-9]*))?",
                             priority=4, block=True)


    @ranking_query.handle()
    async def handle_ranking_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        try:
            mode = state["_matched_groups"][0]
            start = state["_matched_groups"][2]
            end = state["_matched_groups"][3]

            if mode is None:
                mode = conf.pixiv_ranking_default_mode
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

            if start is None or end is None:
                start, end = conf.pixiv_ranking_default_range
            else:
                start = int(start)
                end = int(end)

            if end - start + 1 > conf.pixiv_ranking_max_item_per_msg:
                await matcher.send(f"仅支持一次查询{conf.pixiv_ranking_max_item_per_msg}张以下插画")
            elif start > end:
                await matcher.send("范围不合法")
            elif end > conf.pixiv_ranking_fetch_item:
                await matcher.send(f'仅支持查询{conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await data_source.illust_ranking(mode)
                msg = await make_illusts_msg(illusts[start - 1:end], start)
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

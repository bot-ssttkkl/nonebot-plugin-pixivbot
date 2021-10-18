# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..query_error import QueryError
from ..data_source import data_source
from ..msg_maker import make_illust_msg
from ..utils import random_illust

random_bookmark_query = on_regex("来张私家车", rule=to_me(), priority=5)


@random_bookmark_query.handle()
async def handle_random_bookmark_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        illusts = await data_source.user_bookmarks(6059616, None, 1000, 40)

        if len(illusts) > 0:
            illust = random_illust(illusts, "uniform")
            logger.debug(f"{len(illusts)} bookmarks found, select {illust.title} ({illust.id}).")
            msg = await make_illust_msg(illust)
            await matcher.send(msg)
        else:
            await matcher.send("没有书签")
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except Exception as e:
        logger.exception(e)

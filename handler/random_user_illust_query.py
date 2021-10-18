# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..query_error import QueryError
from ..msg_maker import make_illust_msg
from ..data_source import data_source
from ..model.User import User
from ..utils import random_illust

random_user_illust_query = on_regex("来张(.+)老师的图", rule=to_me(), priority=4, block=True)


@random_user_illust_query.handle()
async def handle_random_user_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        keyword = state["_matched_groups"][0]
        users = await data_source.search_user(keyword)
        if len(users) == 0:
            await matcher.send("找不到相关用户")
        else:
            user_id = users[0].id
            illusts = await data_source.user_illusts(user_id, None, 500, 20)

            if len(illusts) > 0:
                illust = random_illust(illusts, "uniform")
                logger.debug(
                    f"{len(illusts)} illusts with keyword \"{keyword}\" found, select {illust.title} ({illust.id}).")
                msg = await make_illust_msg(illust)
                await matcher.send(msg)
            else:
                await matcher.send("找不到相关图片")
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except Exception as e:
        logger.exception(e)

# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..illust_msg_maker import make_illust_msg
from ..pixiv import api as papi
from ..utils import random_illust, flat_page

random_illust_query = on_regex("来张(.*)图", rule=to_me(), priority=5)


@random_illust_query.handle()
async def handle_random_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        keyword = state["_matched_groups"][0]

        result = await flat_page(papi(), papi().search_illust, None, 500, 20, word=keyword)
        if result.error is not None:
            # error occurred
            logger.warning(result.error)

        if len(result.illusts) > 0:
            illust = random_illust(result.illusts, "bookmark_proportion")
            logger.debug(f"{len(result.illusts)} illusts with keyword \"{keyword}\" found, select {illust.title} ({illust.id}).")
            msg = await make_illust_msg(illust)
            await matcher.send(msg)
        else:
            await matcher.send("找不到相关图片")
    except Exception as e:
        logger.exception(e)

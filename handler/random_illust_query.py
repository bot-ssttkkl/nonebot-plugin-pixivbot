# import nonebot
from io import BytesIO

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from .. import pixiv_api
from ..pixiv_api import api as papi
from ..random_illust import random_illust

random_illust_query = on_regex("来张(.*)图", rule=to_me(), priority=5)


@random_illust_query.handle()
async def handle_random_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        keyword = state["_matched_groups"][0]

        result = await pixiv_api.flat_page(papi().search_illust, None, 500, 20, word=keyword)
        if result.error is not None:
            # error occurred
            logger.warning(result.error)
            await matcher.send("错误：" + result.error.user_message + result.error.message + result.error.reason)
        else:
            illust = random_illust(result.illusts, "bookmark_proportion")
            with BytesIO() as bio:
                await papi().download(illust.meta_single_page.original_image_url, fname=bio)
                msg = Message(MessageSegment.image(bio))
            await matcher.send(msg)
    except Exception as e:
        logger.exception(e)

# import nonebot
from io import BytesIO

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..model.Result import IllustResult
from ..pixiv_api import api as papi

illust_query = on_regex(r"^看看图\s*([1-9][0-9]*)", rule=to_me(), priority=5)


@illust_query.handle()
async def handle_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        raw_illust_id = state["_matched_groups"][0]
        try:
            illust_id = int(raw_illust_id)
        except ValueError:
            await matcher.reject(raw_illust_id + "不是合法的插画ID")
            return

        raw_result = await papi().illust_detail(illust_id)
        result: IllustResult = IllustResult.parse_obj(raw_result)
        if result.error is not None:
            # error occurred
            logger.warning(result.error)
            await matcher.send("错误：" + result.error.user_message + result.error.message + result.error.reason)
        else:
            with BytesIO() as bio:
                await papi().download(result.illust.meta_single_page.original_image_url, fname=bio)
                msg = Message(MessageSegment.image(bio))
            await matcher.send(msg)
    except Exception as e:
        logger.exception(e)

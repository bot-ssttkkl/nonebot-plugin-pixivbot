# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..illust_msg_maker import make_illust_msg
from ..model.Result import IllustResult
from ..data_source import data_source

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

        result = await data_source.illust_detail(illust_id)
        if result.error is not None:
            # error occurred
            logger.warning(result.error)
            await matcher.send("错误：" + result.error.user_message + result.error.message + result.error.reason)
        else:
            msg = await make_illust_msg(result.illust)
            await matcher.send(msg)
    except Exception as e:
        logger.exception(e)

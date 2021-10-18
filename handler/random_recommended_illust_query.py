# import nonebot

from nonebot import on_regex, on_notice, on_message
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import PokeNotifyEvent, PrivateMessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..data_source import data_source
from ..msg_maker import make_illust_msg
from ..query_error import QueryError
from ..utils import random_illust

random_recommended_illust_query = on_regex("来张图", rule=to_me(), priority=3, block=True)


@random_recommended_illust_query.handle()
async def handle_random_recommended_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    try:
        illusts = await data_source.recommended_illusts(None, 500, 20)

        if len(illusts) > 0:
            illust = random_illust(illusts, "uniform")
            logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await make_illust_msg(illust)
            await matcher.send(msg)
        else:
            await matcher.send("找不到相关图片")
    except QueryError as e:
        await matcher.send(e.reason)
        logger.warning(e)
    except Exception as e:
        logger.exception(e)


async def _group_poke(bot: Bot, event: Event, state: T_State) -> bool:
    return (
            isinstance(event, PokeNotifyEvent)
            and event.is_tome()
    )


group_poke = on_notice(_group_poke, priority=10, block=True)
group_poke.handle()(handle_random_recommended_illust_query)

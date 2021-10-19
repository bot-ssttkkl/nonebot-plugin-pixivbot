# import nonebot

from nonebot import on_regex, on_notice
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import PokeNotifyEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..config import conf
from ..data_source import data_source
from ..errors import QueryError, NoReplyError
from ..msg_maker import make_illust_msg
from ..utils import random_illust

if conf.pixiv_random_recommended_illust_query_enabled:
    random_recommended_illust_query = on_regex("来张图", priority=3, block=True)


    @random_recommended_illust_query.handle()
    async def handle_random_recommended_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        try:
            illusts = await data_source.recommended_illusts(conf.pixiv_random_recommended_illust_max_item,
                                                            conf.pixiv_random_recommended_illust_max_page,
                                                            conf.pixiv_block_tags,
                                                            conf.pixiv_random_recommended_illust_min_bookmark,
                                                            conf.pixiv_random_recommended_illust_min_view)

            if len(illusts) > 0:
                illust = random_illust(illusts, conf.pixiv_random_recommended_illust_method)
                logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
                msg = await make_illust_msg(illust)
                await matcher.send(msg)
            else:
                await matcher.send("别看了，没有的。")
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


    async def _group_poke(bot: Bot, event: Event, state: T_State) -> bool:
        return (
                isinstance(event, PokeNotifyEvent)
                and event.is_tome()
        )


    group_poke = on_notice(_group_poke, priority=10, block=True)
    group_poke.handle()(handle_random_recommended_illust_query)

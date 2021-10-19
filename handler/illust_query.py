# import nonebot

from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..config import conf
from ..data_source import data_source
from ..errors import QueryError, NoReplyError
from ..msg_maker import make_illust_msg

if conf.pixiv_illust_query_enabled:
    illust_query = on_regex(r"看看图\s*([1-9][0-9]*)", priority=5)


    @illust_query.handle()
    async def handle_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        try:
            raw_illust_id = state["_matched_groups"][0]
            try:
                illust_id = int(raw_illust_id)
            except ValueError:
                await matcher.reject(raw_illust_id + "不是合法的插画ID")
                return

            illust = await data_source.illust_detail(illust_id)
            msg = await make_illust_msg(illust)
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

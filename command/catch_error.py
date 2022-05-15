
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..postman import Postman
from .pkg_context import context


postman = context.require(Postman)


def catch_error(wrapped):
    async def func(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        try:
            await wrapped(bot, event, state, matcher)
        except ValueError as e:
            await postman.send_message("参数错误："+str(e), bot=bot, event=event)
        except Exception as e:
            logger.exception(e)
            await postman.send_message("内部错误：" + str(e), bot=bot, event=event)
    return func


__all__ = ("catch_error",)

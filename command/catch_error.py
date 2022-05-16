import asyncio
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State
import pixivpy_async

from ..postman import Postman
from ..errors import *
from .pkg_context import context

postman = context.require(Postman)


def catch_error(wrapped):
    async def func(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        try:
            await wrapped(bot, event, state, matcher)
        except asyncio.TimeoutError:
            logger.warning("Timeout")
            await postman.send_message(f"下载超时", bot=bot, event=event)
        except BadRequestError as e:
            await postman.send_message(str(e), bot=bot, event=event)
        except QueryError as e:
            await postman.send_message(str(e), bot=bot, event=event)
        except Exception as e:
            logger.exception(e)
            await postman.send_message(f"内部错误：{type(e)}{e}", bot=bot, event=event)
    return func


__all__ = ("catch_error",)

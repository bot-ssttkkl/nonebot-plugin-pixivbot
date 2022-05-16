# import nonebot
from datetime import datetime

from nonebot import on_regex, on_notice
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import PokeNotifyEvent, MessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from ..config import Config
from ..controller import Service
from ..postman import Postman
from ..utils import decode_integer
from ..handler import *
from ..errors import BadRequestError
from .pkg_context import context
from .catch_error import catch_error

conf = context.require(Config)
service = context.require(Service)
postman = context.require(Postman)


last_query_time = {}


@catch_error
async def cooldown_interceptor(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    if not isinstance(event, MessageEvent) or conf.pixiv_query_cooldown == 0 \
            or event.user_id in conf.pixiv_no_query_cooldown_users:
        return

    now = datetime.now()
    if event.user_id not in last_query_time:
        last_query_time[event.user_id] = now
    else:
        delta = now - last_query_time[event.user_id]
        if delta.total_seconds() >= conf.pixiv_query_cooldown:
            last_query_time[event.user_id] = now
        else:
            await matcher.finish(f"你的CD还有{int(conf.pixiv_query_cooldown - delta.total_seconds())}s转好")


if conf.pixiv_ranking_query_enabled:
    mat = on_regex(r"^看看(.*)?榜\s*(.*)?$", priority=4, block=True)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_ranking_nth_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        mode = state["_matched_groups"][0]
        num = state["_matched_groups"][1]

        handler = context.require(RankingHandler)
        kwargs = handler.parse_command_args((mode, num), event.user_id)
        await handler.handle(bot=bot, event=event, **kwargs)


if conf.pixiv_illust_query_enabled:
    mat = on_regex(r"^看看图\s*([1-9][0-9]*)$", priority=5)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        illust_id = state["_matched_groups"][0]

        handler = context.require(IllustHandler)
        kwargs = handler.parse_command_args((illust_id,), event.user_id)
        await handler.handle(bot=bot, event=event, **kwargs)


if conf.pixiv_random_recommended_illust_query_enabled:
    mat = on_regex("^来(.*)?张图$", priority=3, block=True)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_random_recommended_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        count = state["_matched_groups"][0]
        if count:
            try:
                count = decode_integer(count)
            except:
                raise BadRequestError(f"{count}不是合法的数字")
        else:
            count = 1

        handler = context.require(RandomRecommendedIllustHandler)
        await handler.handle(count=count, bot=bot, event=event)


if conf.pixiv_random_user_illust_query_enabled:
    mat = on_regex("^来(.*)?张(.+)老师的图$", priority=4, block=True)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_random_user_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        count = state["_matched_groups"][0]
        user = state["_matched_groups"][1]

        if count:
            try:
                count = decode_integer(count)
            except:
                raise BadRequestError(f"{count}不是合法的数字")
        else:
            count = 1

        handler = context.require(RandomUserIllustHandler)
        await handler.handle(user, count=count, bot=bot, event=event)


if conf.pixiv_random_bookmark_query_enabled:
    mat = on_regex("^来(.*)?张私家车$", priority=5)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_random_bookmark_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        count = state["_matched_groups"][0]

        if count:
            try:
                count = decode_integer(count)
            except:
                raise BadRequestError(f"{count}不是合法的数字")
        else:
            count = 1

        handler = context.require(RandomBookmarkHandler)
        await handler.handle(event.user_id, count=count, bot=bot, event=event)


if conf.pixiv_random_illust_query_enabled:
    mat = on_regex("^来(.*)?张(.+)图$", priority=5)
    mat.append_handler(cooldown_interceptor)

    @mat.handle()
    @catch_error
    async def handle_random_illust_query(bot: Bot, event: Event, state: T_State, matcher: Matcher):
        count = state["_matched_groups"][0]
        word = state["_matched_groups"][1]

        if count:
            try:
                count = decode_integer(count)
            except:
                raise BadRequestError(f"{count}不是合法的数字")
        else:
            count = 1

        handler = context.require(RandomIllustHandler)
        await handler.handle(word, count=count, bot=bot, event=event)


# async def handle_redistribute(bot: Bot, event: Event, state: T_State, matcher: Matcher):
#     await distributor.redistribute(bot=bot, event=event)


# async def handle_related_illust(bot: Bot, event: Event, state: T_State, matcher: Matcher):
#     await distributor.distribute_related_illust(bot=bot, event=event)


# if conf.pixiv_more_enabled:
#     mat = on_regex("^还要$", priority=1, block=True)
#     mat.append_handler(cooldown_interceptor)
#     mat.append_handler(handle_redistribute)

# if conf.pixiv_random_related_illust_query_enabled:
#     mat = on_regex("^不够色$", priority=1, block=True)
#     mat.append_handler(cooldown_interceptor)
#     mat.append_handler(handle_related_illust)


if conf.pixiv_poke_action:
    handler = locals().get(f'handle_{conf.pixiv_poke_action}_query', None)
    if handler:
        async def _group_poke(event: Event) -> bool:
            return isinstance(event, PokeNotifyEvent) and event.is_tome()

        group_poke = on_notice(_group_poke, priority=10, block=True)
        group_poke.append_handler(cooldown_interceptor)
        group_poke.append_handler(handler)
    else:
        logger.warning(
            f"Bot will not respond to poke since {conf.pixiv_poke_action} is disabled.")

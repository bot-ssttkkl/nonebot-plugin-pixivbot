from nonebot import Bot
from nonebot.internal.adapter import Event
from nonebot.rule import to_me
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestinationFactoryManager
from nonebot_plugin_pixivbot.utils.decode_integer import decode_integer
from nonebot_plugin_pixivbot.utils.errors import BadRequestError


def get_count(state: T_State, pos: int = 0):
    count = 1
    if "_matched_groups" in state:
        raw_count = state["_matched_groups"][pos]
        if raw_count:
            try:
                count = decode_integer(raw_count)
            except:
                raise BadRequestError(f"{raw_count}不是合法的数字")
    return count


def get_common_query_rule():
    if context.require(Config).pixiv_query_to_me_only:
        rule = to_me()
    else:
        rule = None
    return rule


def get_command_rule():
    if context.require(Config).pixiv_command_to_me_only:
        rule = to_me()
    else:
        rule = None
    return rule


def get_post_dest(bot: Bot, event: Event):
    return context.require(PostDestinationFactoryManager).from_event(bot, event)


__all__ = ("get_count", "get_common_query_rule", "get_command_rule", "get_post_dest")

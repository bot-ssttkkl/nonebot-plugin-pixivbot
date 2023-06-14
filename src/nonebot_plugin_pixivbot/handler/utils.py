from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot.rule import to_me

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.decode_integer import decode_integer
from nonebot_plugin_pixivbot.utils.errors import BadRequestError


def ArgCount(pos: int = 0):
    def dep(matched_groups=RegexGroup()):
        count = 1
        if matched_groups:
            raw_count = matched_groups[pos]
            if raw_count:
                try:
                    count = decode_integer(raw_count)
                except ValueError:
                    raise BadRequestError(f"{raw_count}不是合法的数字")
        return count

    return Depends(dep)


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


__all__ = ("get_count", "get_common_query_rule", "get_command_rule", "get_post_dest")

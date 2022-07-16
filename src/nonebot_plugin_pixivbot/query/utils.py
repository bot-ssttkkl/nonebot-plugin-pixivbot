from nonebot.typing import T_State

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


__all__ = ("get_count",)

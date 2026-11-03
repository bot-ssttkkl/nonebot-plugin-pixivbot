import re
from typing import Iterable, Optional

from nonebot import get_driver, on_message
from nonebot.consts import REGEX_MATCHED
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot.rule import Rule, to_me
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.decode_integer import decode_integer
from nonebot_plugin_pixivbot.utils.errors import BadRequestError


class NLRegexChecker:
    """
    与 NoneBot 的 RegexRule 类似，但会忽略 CQ 码，并允许消息带 COMMAND_START 前缀。

    匹配顺序：
    1. 先用消息纯文本匹配；
    2. 若不匹配，再尝试去掉配置中的命令前缀后匹配。

    先匹配原文是为了避免命令前缀恰好是普通语句开头字符时误截断，
    例如 COMMAND_START 配置为 "看" 时，"看看周榜" 仍应正常匹配。
    """

    def __init__(self, pattern: str, flags: int = 0,
                 command_starts: Optional[Iterable[str]] = None):
        self.regex = re.compile(pattern, flags)
        self._command_starts = (
            None if command_starts is None else tuple(command_starts)
        )

    def _starts(self) -> list:
        starts = self._command_starts
        if starts is None:
            starts = get_driver().config.command_start

        # 长前缀优先，例如同时配置 # 和 ## 时先尝试 ##
        return sorted(
            (start for start in starts if start),
            key=len,
            reverse=True,
        )

    async def __call__(self, event: Event, state: T_State) -> bool:
        try:
            text = (event.get_plaintext() or "").strip()
        except Exception:
            return False

        candidates = [text]

        for start in self._starts():
            if text.startswith(start):
                candidates.append(text[len(start):].lstrip())

        for candidate in candidates:
            if matched := self.regex.search(candidate):
                state[REGEX_MATCHED] = matched
                return True

        return False


def nl_regex(pattern: str, flags: int = 0) -> Rule:
    return Rule(NLRegexChecker(pattern, flags))


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


def on_nl_regex(pattern: str, flags: int = 0, **kwargs):
    """
    注册一个普通语句 matcher。

    与 on_regex 的区别是：
    - 匹配消息纯文本，而不是包含 CQ 码的 str(message)；
    - 允许消息带 COMMAND_START 前缀。
    """
    rule = nl_regex(pattern, flags)

    extra_rule = get_common_query_rule()
    if extra_rule is not None:
        rule = rule & extra_rule

    # 与 on_regex 一样，把 matcher 的 source 指回调用方模块，而不是本文件
    return on_message(rule=rule, _depth=1, **kwargs)


def get_command_rule():
    if context.require(Config).pixiv_command_to_me_only:
        rule = to_me()
    else:
        rule = None
    return rule


__all__ = ("NLRegexChecker", "nl_regex", "on_nl_regex",
           "get_common_query_rule", "get_command_rule")

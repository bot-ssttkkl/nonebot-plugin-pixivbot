"""
nonebot-plugin-pixivbot

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""

from .global_context import context
from .providers import provide
from .query import QueryManager

provide(context)

__all__ = ("context",)

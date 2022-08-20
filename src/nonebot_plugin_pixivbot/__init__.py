"""
nonebot-plugin-pixivbot

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""

# ================= provide beans =================
from importlib import import_module

from nonebot import logger

from .global_context import context
from .providers import provide

provide(context)

# =========== register query & service ============
from . import query
from . import service

# ============== load custom protocol =============
supported_modules = ["nonebot_plugin_pixivbot_onebot_v11", "nonebot_plugin_pixivbot_kook"]

for p in supported_modules:
    try:
        import_module(p)
        logger.success("Loaded Module: " + p)
    except ModuleNotFoundError:
        pass

__all__ = ("context",)

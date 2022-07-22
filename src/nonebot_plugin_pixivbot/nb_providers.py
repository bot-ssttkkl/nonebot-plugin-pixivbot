from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler
from nonebot import require

from nonebot_plugin_pixivbot.context import Context


def asyncio_scheduler_provider(context: Context):
    context.register_lazy(AsyncIOScheduler, lambda: require("nonebot_plugin_apscheduler").scheduler)


def base_scheduler_provider(context: Context):
    context.bind_to(BaseScheduler, AsyncIOScheduler)


providers = [asyncio_scheduler_provider, base_scheduler_provider]


def provide(context: Context):
    for p in providers:
        p(context)


__all__ = ("provide",)

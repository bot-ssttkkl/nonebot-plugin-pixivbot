from nonebot import require

from nonebot_plugin_access_control.service import PluginService
from nonebot_plugin_pixivbot.context import Context


def asyncio_scheduler_provider(context: Context):
    # 改成register_lazy以后Scheduler不工作，不懂为啥
    require("nonebot_plugin_apscheduler")

    from nonebot_plugin_apscheduler import scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    context.register(AsyncIOScheduler, scheduler)


def base_scheduler_provider(context: Context):
    from apscheduler.schedulers.base import BaseScheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    context.bind(BaseScheduler, AsyncIOScheduler)


def plugin_service_provider(context: Context):
    from .plugin_service import plugin_service
    context.register(PluginService, plugin_service)


providers = [asyncio_scheduler_provider, base_scheduler_provider, plugin_service_provider]


def provide(context: Context):
    for p in providers:
        p(context)


__all__ = ("provide",)

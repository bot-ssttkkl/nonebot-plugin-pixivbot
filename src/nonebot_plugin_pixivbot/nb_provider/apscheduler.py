from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler
from nonebot import require

from nonebot_plugin_pixivbot.utils.context import Context


def asyncio_scheduler_provider(context: Context):
    context.register_lazy(AsyncIOScheduler, lambda: require("nonebot_plugin_apscheduler").scheduler)


def base_scheduler_provider(context: Context):
    context.bind(BaseScheduler, AsyncIOScheduler)


providers = [asyncio_scheduler_provider, base_scheduler_provider]

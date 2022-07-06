from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler
from nonebot import require

from .global_context import global_context as context


@context.register_factory(AsyncIOScheduler)
def apscheduler():
    return require("nonebot_plugin_apscheduler").scheduler


context.bind(BaseScheduler, AsyncIOScheduler)

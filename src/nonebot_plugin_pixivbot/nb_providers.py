from nonebot_plugin_pixivbot.context import Context


def asyncio_scheduler_provider(context: Context):
    # 改成register_lazy以后Scheduler不工作，不懂为啥
    from nonebot import require

    require("nonebot_plugin_apscheduler")

    from nonebot_plugin_apscheduler import scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    context.register(AsyncIOScheduler, scheduler)


def base_scheduler_provider(context: Context):
    from apscheduler.schedulers.base import BaseScheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    context.bind(BaseScheduler, AsyncIOScheduler)


providers = [asyncio_scheduler_provider, base_scheduler_provider]


def provide(context: Context):
    for p in providers:
        p(context)


__all__ = ("provide",)

from inspect import isawaitable
import re
import typing
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger, get_driver
from nonebot.adapters.onebot.v11 import Bot

from ..data_source import Subscriptions
from ..postman import Postman
from ..handler import *
from ..errors import BadRequestError
from .pkg_context import context
from .pixiv_service import PixivService


@context.root.register_singleton()
class Scheduler:
    apscheduler = context.require(AsyncIOScheduler)
    subscriptions = context.require(Subscriptions)
    service = context.require(PixivService)
    postman = context.require(Postman)

    @staticmethod
    def _make_job_id(type: str, user_id: typing.Optional[int], group_id: typing.Optional[int]):
        if group_id:
            return f'scheduled {type} g{group_id}'
        else:
            return f'scheduled {type} u{user_id}'

    @staticmethod
    def _parse_schedule(raw_schedule: str) -> typing.Sequence[int]:
        start_only_mat = re.fullmatch(r'([0-9]+):([0-9]+)', raw_schedule)
        if start_only_mat is not None:
            g = start_only_mat.groups()
            start_hour, start_minute = int(g[0]), int(g[1])
            interval_hour, interval_minute = 24, 0
        else:
            interval_only_mat = re.fullmatch(
                r'([0-9]+):([0-9]+)\*x', raw_schedule)
            if interval_only_mat is not None:
                g = interval_only_mat.groups()
                start_hour, start_minute = 0, 0
                interval_hour, interval_minute = int(g[0]), int(g[1])
            else:
                mat = re.fullmatch(
                    r'([0-9]+):([0-9]+)\+([0-9]+):([0-9]+)\*x', raw_schedule)
                if mat is not None:
                    g = mat.groups()
                    start_hour, start_minute = int(g[0]), int(g[1])
                    interval_hour, interval_minute = int(g[2]), int(g[3])
                else:
                    raise BadRequestError(f'{raw_schedule}不是合法的时间')

        if start_hour < 0 or start_hour >= 24 or start_minute < 0 or start_minute >= 60 \
                or interval_hour < 0 or interval_minute >= 60 \
                or (interval_hour > 0 and interval_minute < 0) or (interval_hour == 0 and interval_minute <= 0):
            raise BadRequestError(f'{raw_schedule}不是合法的时间')

        return start_hour, start_minute, interval_hour, interval_minute

    async def start(self, bot: Bot):
        async for x in self.subscriptions.get_all():
            user_id = x.get("user_id", None)
            group_id = x.get("group_id", None)

            self._add_job(x["type"], x["schedule"], x["kwargs"],
                          bot=bot, user_id=user_id, group_id=group_id)

    async def stop(self):
        jobs = self.apscheduler.get_jobs()
        for j in jobs:
            if j.id.startswith("scheduled"):
                j.remove()

    _handlers: typing.Dict[str, AbstractHandler] = {
        RandomBookmarkHandler.type(): context.require(RandomBookmarkHandler),
        RandomRecommendedIllustHandler.type(): context.require(RandomRecommendedIllustHandler),
        RankingHandler.type(): context.require(RankingHandler),
        RandomIllustHandler.type(): context.require(RandomIllustHandler),
        RandomUserIllustHandler.type(): context.require(RandomUserIllustHandler),
    }

    def _add_job(self, type: str,
                 schedule: typing.Sequence[int],
                 kwargs: dict = {},
                 *, bot: Bot,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None):
        trigger = IntervalTrigger(hours=schedule[2], minutes=schedule[3],
                                  start_date=datetime.now().replace(hour=schedule[0], minute=schedule[1],
                                                                    second=0, microsecond=0) + timedelta(days=-1))
        job_id = self._make_job_id(type, user_id, group_id)
        self.apscheduler.add_job(self._handlers[type].handle, id=job_id, trigger=trigger,
                                 kwargs={"bot": bot, "user_id": user_id, "group_id": group_id, **kwargs})
        logger.success(f"scheduled {job_id} {trigger}")

    def _remove_job(self, type: str, *,
                    user_id: typing.Optional[int] = None,
                    group_id: typing.Optional[int] = None):
        job_id = self._make_job_id(type, user_id, group_id)
        self.apscheduler.remove_job(job_id)
        logger.success(f"unscheduled {job_id}")

    async def schedule(self, type: str,
                       schedule: typing.Union[str, typing.Sequence[int]],
                       args: list = [],
                       *, bot: Bot,
                       user_id: typing.Optional[int] = None,
                       group_id: typing.Optional[int] = None):
        if type not in self._handlers:
            raise BadRequestError(f"{type}不是合法的类型")

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        kwargs = self._handlers[type].parse_command_args(args, user_id)
        if isawaitable(kwargs):
            kwargs = await kwargs

        old_sub = await self.subscriptions.update(type, user_id, group_id,
                                                  schedule=schedule, kwargs=kwargs)
        if old_sub is not None:
            self._remove_job(type, user_id=user_id, group_id=group_id)
        self._add_job(type, schedule, kwargs,
                      bot=bot, user_id=user_id, group_id=group_id)

    async def unschedule(self, type: str, *,
                         user_id: typing.Optional[int] = None,
                         group_id: typing.Optional[int] = None):
        if type == "all":
            async for x in self.subscriptions.get(user_id, group_id):
                self._remove_job(x["type"], user_id=user_id, group_id=group_id)
        elif type in self._handlers:
            self._remove_job(type, user_id=user_id, group_id=group_id)
        else:
            raise BadRequestError(f"{type}不是合法的类型")

        self.subscriptions.delete(type, user_id, group_id)

    async def all_subscription(self, *,
                               user_id: typing.Optional[int] = None,
                               group_id: typing.Optional[int] = None) -> typing.List[dict]:
        return [x async for x in self.subscriptions.get(user_id, group_id)]


scheduler = context.require(Scheduler)
get_driver().on_bot_connect(scheduler.start)
get_driver().on_bot_disconnect(scheduler.stop)

__all__ = ("Scheduler", )

import re
import typing
from datetime import datetime

from apscheduler.triggers.interval import IntervalTrigger
from nonebot import require, logger, get_driver
from nonebot.adapters.cqhttp import Bot

from .config import conf
from .distributor import distributor, Distributor
from .data_source import subscriptions, Subscriptions


class ScheduledDistributor:
    TYPES = ["ranking", "random_recommended_illust", "random_bookmark"]

    def __init__(self, subscriptions: Subscriptions, distributor: Distributor):
        self.subscriptions = subscriptions
        self.distributor = distributor

    @staticmethod
    def _make_job_id(type: str, user_id: typing.Optional[int], group_id: typing.Optional[int]):
        if user_id is not None:
            return f'scheduled_distribute {type} u{user_id}'
        else:
            return f'scheduled_distribute {type} g{group_id}'

    async def start(self, bot: Bot):
        async for x in self.subscriptions.get():
            if "user_id" in x and x["user_id"] is not None:
                user_id, group_id = x["user_id"], None
            elif "group_id" in x and x["group_id"] is not None:
                user_id, group_id = None, x["group_id"]
            else:
                raise ValueError("Both user_id and group_id is None")

            self._schedule(x["type"], x["schedule"], bot=bot,
                           user_id=user_id, group_id=group_id, **x["kwargs"])

    @staticmethod
    async def stop():
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        jobs = scheduler.get_jobs()
        for j in jobs:
            if j.id.startswith("scheduled_distribute"):
                j.remove()

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
                    raise ValueError(f'illegal schedule: {raw_schedule}')

        if start_hour < 0 or start_hour >= 24 or start_minute < 0 or start_minute >= 60 \
                or interval_hour < 0 or interval_minute >= 60 \
                or (interval_hour > 0 and interval_minute < 0) or (interval_hour == 0 and interval_minute <= 0):
            raise ValueError(f'illegal schedule: {raw_schedule}')

        return start_hour, start_minute, interval_hour, interval_minute

    def _schedule(self, type: str,
                  schedule: typing.Sequence[int], *,
                  bot: Bot,
                  user_id: typing.Optional[int] = None,
                  group_id: typing.Optional[int] = None,
                  **kwargs):
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        trigger = IntervalTrigger(hours=schedule[2], minutes=schedule[3],
                                  start_date=datetime.now().replace(hour=schedule[0], minute=schedule[1],
                                                                    second=0, microsecond=0))
        job_id = self._make_job_id(type, user_id, group_id)
        scheduler.add_job(self.distributor.distribute, id=job_id, trigger=trigger,
                          kwargs={"type": type, "bot": bot, "user_id": user_id, "group_id": group_id,
                                  "silently": True, **kwargs})
        logger.debug(f"scheduled {job_id} {trigger}")

    def _unschedule(self, type: str, *,
                    user_id: typing.Optional[int] = None,
                    group_id: typing.Optional[int] = None):
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        job_id = self._make_job_id(type, user_id, group_id)
        scheduler.remove_job(job_id)
        logger.debug(f"unscheduled {job_id}")

    async def subscribe(self, type: str,
                        schedule: typing.Union[str, typing.Sequence[int]], *,
                        bot: Bot,
                        user_id: typing.Optional[int] = None,
                        group_id: typing.Optional[int] = None,
                        **kwargs):
        if type not in self.TYPES:
            raise ValueError(f"Illegal type: {type}")

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        old_sub = await self.subscriptions.update(type, schedule, user_id, group_id, **kwargs)
        if old_sub is not None:
            self._unschedule(type, user_id=user_id, group_id=group_id)
        self._schedule(type, schedule, bot=bot, user_id=user_id,
                       group_id=group_id, **kwargs)

    async def unsubscribe(self, type: str, *,
                          user_id: typing.Optional[int] = None,
                          group_id: typing.Optional[int] = None):
        if type != "all" and type not in self.TYPES:
            raise ValueError(f"Illegal type: {type}")

        if type != "all":
            self._unschedule(type, user_id=user_id, group_id=group_id)
        else:
            async for x in self.subscriptions.get(user_id, group_id):
                self._unschedule(x["type"], user_id=user_id, group_id=group_id)
        self.subscriptions.delete(type, user_id, group_id)

    async def all_subscription(self, *,
                               user_id: typing.Optional[int] = None,
                               group_id: typing.Optional[int] = None) -> typing.List[dict]:
        return [x async for x in self.subscriptions.get(user_id, group_id)]


sch_distributor = ScheduledDistributor(subscriptions, distributor)


get_driver().on_bot_connect(sch_distributor.start)
get_driver().on_bot_disconnect(sch_distributor.stop)

__all__ = ("ScheduledDistributor", "sch_distributor")

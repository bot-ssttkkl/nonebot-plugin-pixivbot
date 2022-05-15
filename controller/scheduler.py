import re
import typing
from datetime import datetime, timedelta

from apscheduler.triggers.interval import IntervalTrigger
from nonebot import require, logger, get_driver
from nonebot.adapters.onebot.v11 import Bot

from ..data_source import Subscriptions
from ..postman import Postman
from .service import Service
from .pkg_context import context


@context.export_singleton()
class Scheduler:
    apscheduler = require("nonebot_plugin_apscheduler").scheduler

    subscriptions = context.require(Subscriptions)
    service = context.require(Service)
    postman = context.require(Postman)

    @staticmethod
    def _make_job_id(type: str, user_id: typing.Optional[int], group_id: typing.Optional[int]):
        if user_id is not None:
            return f'scheduled {type} u{user_id}'
        else:
            return f'scheduled {type} g{group_id}'

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

    async def start(self, bot: Bot):
        async for x in self.subscriptions.get():
            if "user_id" in x and x["user_id"] is not None:
                user_id, group_id = x["user_id"], None
            elif "group_id" in x and x["group_id"] is not None:
                user_id, group_id = None, x["group_id"]
            else:
                raise ValueError("Both user_id and group_id are None")

            self._add_job(x["type"], x["schedule"], x["kwargs"],
                          bot=bot, user_id=user_id, group_id=group_id)

    async def stop(self):
        jobs = self.apscheduler.get_jobs()
        for j in jobs:
            if j.id.startswith("scheduled"):
                j.remove()

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
        self.apscheduler.add_job(self._handlers[type], id=job_id, trigger=trigger,
                                 kwargs={"self": self, "bot": bot, "user_id": user_id, "group_id": group_id, **kwargs})
        logger.success(f"scheduled {job_id} {trigger}")

    def _remove_job(self, type: str, *,
                    user_id: typing.Optional[int] = None,
                    group_id: typing.Optional[int] = None):
        job_id = self._make_job_id(type, user_id, group_id)
        self.apscheduler.remove_job(job_id)
        logger.success(f"unscheduled {job_id}")

    async def _handle_ranking(self, mode: typing.Optional[str] = None,
                              range: typing.Optional[typing.Union[typing.Sequence[int], int]] = None,
                              *, bot: Bot,
                              user_id: typing.Optional[int] = None,
                              group_id: typing.Optional[int] = None):
        illusts = await self.service.illust_ranking(mode, range)
        await self.postman.send_illusts(illusts, number=range[0] if range else 1,
                                        bot=bot, user_id=user_id, group_id=group_id)

    async def _handle_random_recommended_illust(self,
                                                *, bot: Bot,
                                                user_id: typing.Optional[int] = None,
                                                group_id: typing.Optional[int] = None):
        illusts = await self.service.random_recommended_illust()
        await self.postman.send_illusts(
            illusts, bot=bot, user_id=user_id, group_id=group_id)

    async def _handle_random_bookmark(self, pixiv_user_id: int = 0,
                                      *, bot: Bot,
                                      user_id: typing.Optional[int] = None,
                                      group_id: typing.Optional[int] = None):
        illusts = await self.service.random_bookmark(user_id, pixiv_user_id)
        await self.postman.send_illusts(
            illusts, bot=bot, user_id=user_id, group_id=group_id)

    _handlers = {
        "ranking": _handle_ranking,
        "random_recommended_illust": _handle_random_recommended_illust,
        "random_bookmark": _handle_random_bookmark,
    }

    def _args_to_kwargs(self, type: str, args: list = []) -> dict:
        if type == "ranking":
            mode = args[0] if len(args) > 0 else None
            range = args[1] if len(args) > 1 else None
            self.service.validate_illust_ranking_args(mode, range)
            return {"mode": mode, "range": range}
        elif type == "random_recommended_illust":
            return {}
        elif type == "random_bookmark":
            pixiv_user_id = args[0] if len(args) > 0 else 0
            return {"pixiv_user_id": pixiv_user_id}

    async def schedule(self, type: str,
                       schedule: typing.Union[str, typing.Sequence[int]],
                       args: list = [],
                       *, bot: Bot,
                       user_id: typing.Optional[int] = None,
                       group_id: typing.Optional[int] = None):
        if type not in self._handlers:
            raise ValueError(f"Illegal type: {type}")

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        kwargs = self._args_to_kwargs(type, args)
        old_sub = await self.subscriptions.update(type, user_id, group_id,
                                                  schedule=schedule, kwargs=kwargs)
        if old_sub is not None:
            self._remove_job(type, user_id=user_id, group_id=group_id)
        self._add_job(type, schedule, kwargs,
                      bot=bot, user_id=user_id, group_id=group_id)

    async def unschedule(self, type: str, *,
                         user_id: typing.Optional[int] = None,
                         group_id: typing.Optional[int] = None):
        if type != "all" and type not in self._handlers:
            raise ValueError(f"Illegal type: {type}")

        if type != "all":
            self._remove_job(type, user_id=user_id, group_id=group_id)
        else:
            async for x in self.subscriptions.get(user_id, group_id):
                self._remove_job(x["type"], user_id=user_id, group_id=group_id)
        self.subscriptions.delete(type, user_id, group_id)

    async def all_subscription(self, *,
                               user_id: typing.Optional[int] = None,
                               group_id: typing.Optional[int] = None) -> typing.List[dict]:
        return [x async for x in self.subscriptions.get(user_id, group_id)]


scheduler = context.require(Scheduler)
get_driver().on_bot_connect(scheduler.start)
get_driver().on_bot_disconnect(scheduler.stop)

__all__ = ("Scheduler", )

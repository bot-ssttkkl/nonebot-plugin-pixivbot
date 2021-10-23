import re
import typing
from datetime import datetime

from apscheduler.triggers.interval import IntervalTrigger
from nonebot import require, logger, get_driver
from nonebot.adapters.cqhttp import Bot
from pymongo import MongoClient, ReturnDocument

from .config import conf
from .distributor import distributor, Distributor


class ScheduledDistributor:
    db_name: str

    TYPES = ["ranking", "random_recommended_illust", "random_bookmark"]

    def __init__(self, db_name: str, distributor: Distributor):
        self.db_name = db_name
        self.distributor = distributor

    @staticmethod
    def _make_job_id(type: str, user_id: typing.Optional[int], group_id: typing.Optional[int]):
        if user_id is not None:
            return f'scheduled_distribute {type} u{user_id}'
        else:
            return f'scheduled_distribute {type} g{group_id}'

    async def start(self, bot: Bot, *,
                    before_distribute: typing.Optional[typing.Callable] = None):
        async for x in self._db.subscription.find():
            if "user_id" in x and x["user_id"] is not None:
                user_id, group_id = x["user_id"], None
            else:
                user_id, group_id = None, x["group_id"]
            self._schedule(x["type"], x["schedule"], bot=bot, user_id=user_id, group_id=group_id,
                           before_distribute=before_distribute, **x["kwargs"])

    @staticmethod
    async def stop():
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        jobs = scheduler.get_jobs()
        for j in jobs:
            if j.id.startswith("scheduled_distribute"):
                j.remove()

    @property
    def _db(self) -> MongoClient:
        db_conn = require("nonebot_plugin_navicat").mongodb_client
        return db_conn[self.db_name]

    @staticmethod
    def _parse_schedule(raw_schedule: str) -> typing.Sequence[int]:
        start_only_mat = re.fullmatch(r'([0-9]+):([0-9]+)', raw_schedule)
        if start_only_mat is not None:
            g = start_only_mat.groups()
            start_hour, start_minute = int(g[0]), int(g[1])
            interval_hour, interval_minute = 24, 0
        else:
            interval_only_mat = re.fullmatch(r'([0-9]+):([0-9]+)\*x', raw_schedule)
            if interval_only_mat is not None:
                g = interval_only_mat.groups()
                start_hour, start_minute = 0, 0
                interval_hour, interval_minute = int(g[0]), int(g[1])
            else:
                mat = re.fullmatch(r'([0-9]+):([0-9]+)\+([0-9]+):([0-9]+)\*x', raw_schedule)
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
                  before_distribute: typing.Optional[typing.Callable] = None,
                  **kwargs):
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        trigger = IntervalTrigger(hours=schedule[2], minutes=schedule[3],
                                  start_date=datetime.now().replace(hour=schedule[0], minute=schedule[1],
                                                                    second=0, microsecond=0))
        job_id = self._make_job_id(type, user_id, group_id)

        if before_distribute is not None:
            async def j(**k):
                await before_distribute(**k)
                await self.distributor.distribute(**k)

            scheduler.add_job(j, id=job_id, trigger=trigger,
                              kwargs={"type": type, "bot": bot, "user_id": user_id, "group_id": group_id,
                                      "no_error_msg": True, **kwargs})
        else:
            scheduler.add_job(self.distributor.distribute, id=job_id, trigger=trigger,
                              kwargs={"type": type, "bot": bot, "user_id": user_id, "group_id": group_id,
                                      "no_error_msg": True, **kwargs})
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
                        before_distribute: typing.Optional[typing.Callable] = None,
                        **kwargs):
        if type not in self.TYPES:
            raise ValueError(f"Illegal type: {type}")

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        if user_id is None and group_id is not None:
            query = {"type": type, "group_id": group_id}
        elif user_id is not None and group_id is None:
            query = {"type": type, "user_id": user_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        old_sub = await self._db.subscription.find_one_and_replace(query, {**query,
                                                                           "schedule": schedule,
                                                                           "kwargs": kwargs},
                                                                   return_document=ReturnDocument.BEFORE,
                                                                   upsert=True)
        if old_sub is not None:
            self._unschedule(type, user_id=user_id, group_id=group_id)
        self._schedule(type, schedule, bot=bot, user_id=user_id, group_id=group_id,
                       before_distribute=before_distribute, **kwargs)

    async def unsubscribe(self, type: str, *,
                          user_id: typing.Optional[int] = None,
                          group_id: typing.Optional[int] = None):
        if type != "all" and type not in self.TYPES:
            raise ValueError(f"Illegal type: {type}")

        if user_id is None and group_id is not None:
            query = {"type": type, "user_id": user_id}
        elif user_id is not None and group_id is None:
            query = {"type": type, "group_id": group_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        if type != "all":
            await self._db.subscription.delete_one(query)
            self._unschedule(type, user_id=user_id, group_id=group_id)
        else:
            del query["type"]
            async for x in self._db.subscription.find(query):
                self._unschedule(x["type"], user_id=user_id, group_id=group_id)
            await self._db.subscription.delete_many(query)

    async def all_subscription(self, *,
                               user_id: typing.Optional[int] = None,
                               group_id: typing.Optional[int] = None) -> typing.List[dict]:
        if user_id is None and group_id is not None:
            query = {"user_id": user_id}
        elif user_id is not None and group_id is None:
            query = {"group_id": group_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        ans = []
        async for x in self._db.subscription.find(query):
            ans.append({"type": x["type"], "schedule": x["schedule"], **query, **x["kwargs"]})
        return ans


# async def before_distribute(bot: Bot,
#                             user_id: typing.Optional[int] = None,
#                             group_id: typing.Optional[int] = None, **kwargs):
#     await bot.send_msg(user_id=user_id, group_id=group_id, message="这是您点的图")


sch_distributor = ScheduledDistributor(conf.pixiv_mongo_database_name, distributor)


@get_driver().on_bot_connect
async def start_sch_distributor(bot: Bot):
    await sch_distributor.start(bot)


get_driver().on_bot_disconnect(sch_distributor.stop)

__all__ = ("ScheduledDistributor", "sch_distributor")

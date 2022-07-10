import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import TypeVar, Dict, List, Sequence, Union, Optional, Generic

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from lazy import lazy
from nonebot import Bot, logger, get_driver

from nonebot_plugin_pixivbot.data.subscription_repo import SubscriptionRepo
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model import Subscription
from nonebot_plugin_pixivbot.postman import PostIdentifier, PostDestinationFactory
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
# B = TypeVar("B", bound=Bot)
# M = TypeVar("M", bound=Message)

ID = PostIdentifier[UID, GID]


@context.register_singleton()
class Scheduler(Generic[UID, GID]):
    apscheduler = context.require(AsyncIOScheduler)
    subscriptions = context.require(SubscriptionRepo)
    post_dest_factory = context.require(PostDestinationFactory)

    @staticmethod
    def _make_job_id(type: str, identifier: PostIdentifier[UID, GID]):
        if identifier.group_id:
            return f'scheduled {type} g{identifier.group_id}'
        else:
            return f'scheduled {type} u{identifier.user_id}'

    @staticmethod
    def _parse_schedule(raw_schedule: str) -> Sequence[int]:
        start_only_mat = re.fullmatch(r'(\d+):(\d+)', raw_schedule)
        if start_only_mat is not None:
            g = start_only_mat.groups()
            start_hour, start_minute = int(g[0]), int(g[1])
            interval_hour, interval_minute = 24, 0
        else:
            interval_only_mat = re.fullmatch(
                r'(\d+):(\d+)\*x', raw_schedule)
            if interval_only_mat is not None:
                g = interval_only_mat.groups()
                start_hour, start_minute = 0, 0
                interval_hour, interval_minute = int(g[0]), int(g[1])
            else:
                mat = re.fullmatch(r'(\d+):(\d+)\+(\d+):(\d+)\*x', raw_schedule)
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
        async for subscription in self.subscriptions.get_all():
            self._add_job(subscription, bot)

    async def stop(self):
        jobs = self.apscheduler.get_jobs()
        for j in jobs:
            if j.id.startswith("scheduled"):
                j.remove()

    @lazy
    def _handlers(self) -> Dict[str, 'Handler']:
        # 解决Handler和Scheduler的循环引用
        from nonebot_plugin_pixivbot.handler import RandomBookmarkHandler, RandomRecommendedIllustHandler, \
            RankingHandler, RandomIllustHandler, RandomUserIllustHandler
        return {
            RandomBookmarkHandler.type(): context.require(RandomBookmarkHandler),
            RandomRecommendedIllustHandler.type(): context.require(RandomRecommendedIllustHandler),
            RankingHandler.type(): context.require(RankingHandler),
            RandomIllustHandler.type(): context.require(RandomIllustHandler),
            RandomUserIllustHandler.type(): context.require(RandomUserIllustHandler),
        }

    def _add_job(self, sub: Subscription[UID, GID], bot: Bot):
        offset_hour, offset_minute, hours, minutes = sub.schedule
        trigger = IntervalTrigger(hours=hours, minutes=minutes,
                                  start_date=datetime.now().replace(hour=offset_hour, minute=offset_minute,
                                                                    second=0, microsecond=0) + timedelta(days=-1))
        job_id = self._make_job_id(sub.type, sub.identifier)
        post_dest = self.post_dest_factory.from_id(bot, PostIdentifier(sub.user_id, sub.group_id))
        self.apscheduler.add_job(self._handlers[sub.type].handle, id=job_id, trigger=trigger,
                                 kwargs={"post_dest": post_dest, "silently": True, **sub.kwargs})
        logger.success(f"scheduled {job_id} {trigger}")

    def _remove_job(self, type: str, identifier: PostIdentifier[UID, GID]):
        job_id = self._make_job_id(type, identifier)
        self.apscheduler.remove_job(job_id)
        logger.success(f"unscheduled {job_id}")

    async def schedule(self, type: str,
                       schedule: Union[str, Sequence[int]],
                       args: Optional[list] = None,
                       *, bot: Bot,
                       identifier: PostIdentifier[UID, GID]):
        if type not in self._handlers:
            raise BadRequestError(f"{type}不是合法的类型")

        if args is None:
            args = []

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        kwargs = self._handlers[type].parse_args(args, identifier)
        if isawaitable(kwargs):
            kwargs = await kwargs

        sub = Subscription(user_id=identifier.user_id,
                           group_id=identifier.group_id,
                           type=type,
                           schedule=schedule,
                           kwargs=kwargs)

        old_sub = await self.subscriptions.update(sub)
        if old_sub is not None:
            self._remove_job(sub.type, sub.identifier)
        self._add_job(sub, bot)

    async def unschedule(self, type: str, identifier: PostIdentifier[UID, GID]):
        if type == "all":
            async for sub in self.subscriptions.get(identifier):
                self._remove_job(sub.type, identifier)
        elif type in self._handlers:
            self._remove_job(type, identifier)
        else:
            raise BadRequestError(f"{type}不是合法的类型")

        await self.subscriptions.delete(type, identifier)

    async def all_subscription(self, identifier: PostIdentifier[UID, GID]) -> List[dict]:
        return [x async for x in self.subscriptions.get(identifier)]


scheduler = context.require(Scheduler)
get_driver().on_bot_connect(scheduler.start)
get_driver().on_bot_disconnect(scheduler.stop)

__all__ = ("Scheduler",)

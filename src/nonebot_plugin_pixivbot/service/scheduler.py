from __future__ import annotations

import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import TypeVar, Dict, List, Sequence, Union, Optional, TYPE_CHECKING

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from lazy import lazy
from nonebot import logger, Bot
from nonebot.exception import ActionFailed

from nonebot_plugin_pixivbot.data.subscription_repo import SubscriptionRepo
from nonebot_plugin_pixivbot.data.utils.process_subscriber import process_subscriber
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier
from nonebot_plugin_pixivbot.model.subscription import ScheduleType
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect, on_bot_disconnect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler import Handler

UID = TypeVar("UID")
GID = TypeVar("GID")


def parse_schedule(raw_schedule: str) -> Sequence[int]:
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
            mat = re.fullmatch(
                r'(\d+):(\d+)\+(\d+):(\d+)\*x', raw_schedule)
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


@context.inject
@context.register_eager_singleton()
class Scheduler:
    apscheduler: AsyncIOScheduler
    repo: SubscriptionRepo
    pd_factory_mgr: PostDestinationFactoryManager
    auth_mgr: AuthenticatorManager

    def __init__(self):
        on_bot_connect(self.on_bot_connect, replay=True)
        on_bot_disconnect(self.on_bot_disconnect)

    @staticmethod
    def _make_job_id(type: ScheduleType, identifier: PostIdentifier[UID, GID]):
        return f'scheduler {type.name} {identifier}'

    @lazy
    def _handlers(self) -> Dict[ScheduleType, Handler]:
        # 解决Handler和Scheduler的循环引用
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler, RandomRecommendedIllustHandler, \
            RankingHandler, RandomIllustHandler, RandomUserIllustHandler
        return {
            ScheduleType.random_bookmark: context.require(RandomBookmarkHandler),
            ScheduleType.random_recommended_illust: context.require(RandomRecommendedIllustHandler),
            ScheduleType.ranking: context.require(RankingHandler),
            ScheduleType.random_illust: context.require(RandomIllustHandler),
            ScheduleType.random_user_illust: context.require(RandomUserIllustHandler),
        }

    async def _on_trigger(self, sub: Subscription[UID, GID], post_dest: PostDestination[UID, GID]):
        job_id = self._make_job_id(sub.type, sub.subscriber)
        logger.info(f"[scheduler] triggered {job_id}")

        try:
            await self._handlers[sub.type].handle_with_parsed_args(post_dest=post_dest, silently=True, **sub.kwargs)
        except ActionFailed as e:
            logger.warning("[scheduler] ActionFailed: " + str(e))

            available = self.auth_mgr.available(post_dest)
            if isawaitable(available):
                available = await available

            if not available:
                logger.info(f"[scheduler] {post_dest} is no longer available, removing all his subscriptions...")
                await self.unschedule_all_by_subscriber(post_dest.identifier)

    def _add_job(self, post_dest: PostDestination[UID, GID], sub: Subscription[UID, GID]):
        offset_hour, offset_minute, hours, minutes = sub.schedule
        tz = pytz.timezone(sub.tz)
        trigger = IntervalTrigger(hours=hours, minutes=minutes,
                                  start_date=datetime.now(tz).replace(hour=offset_hour,
                                                                      minute=offset_minute,
                                                                      second=0,
                                                                      microsecond=0) + timedelta(days=-1))

        job_id = self._make_job_id(sub.type, sub.subscriber)
        self.apscheduler.add_job(self._on_trigger, id=job_id, trigger=trigger,
                                 kwargs={"sub": sub, "post_dest": post_dest})
        logger.success(f"[scheduler] added job \"{job_id}\" on {trigger}")

    def _remove_job(self, sub: Subscription[UID, GID]):
        job_id = self._make_job_id(sub.type, sub.subscriber)
        self.apscheduler.remove_job(job_id)
        logger.success(f"[scheduler] removed job \"{job_id}\"")

    async def on_bot_connect(self, bot: Bot):
        adapter = get_adapter_name(bot)
        async for sub in self.repo.get_by_adapter(adapter):
            post_dest = self.pd_factory_mgr.build(bot, sub.subscriber.user_id, sub.subscriber.group_id)
            self._add_job(post_dest, sub)

    async def on_bot_disconnect(self, bot: Bot):
        async for subscription in self.repo.get_by_adapter(get_adapter_name(bot)):
            try:
                self._remove_job(subscription)
            except Exception as e:
                logger.error(f"[scheduler] error occurred when remove job "
                             f"{self._make_job_id(subscription.type, subscription.subscriber)}")
                logger.exception(e)

    async def schedule(self, type: ScheduleType,
                       schedule: Union[str, Sequence[int]],
                       args: Optional[list] = None,
                       *, post_dest: PostDestination[UID, GID]):
        if args is None:
            args = []

        if isinstance(schedule, str):
            schedule = parse_schedule(schedule)

        kwargs = self._handlers[type].parse_args(args, post_dest)
        if isawaitable(kwargs):
            kwargs = await kwargs

        subscriber_identifier = process_subscriber(post_dest.identifier)
        sub = Subscription(type=type, kwargs=kwargs, subscriber=subscriber_identifier, schedule=schedule)
        old_sub = await self.repo.update(sub)
        if old_sub is not None:
            self._remove_job(sub)
        self._add_job(post_dest.normalized(), sub)

    async def unschedule(self, type: ScheduleType, subscriber: PostIdentifier[UID, GID]) -> bool:
        sub = await self.repo.delete_one(subscriber, type)
        if sub:
            self._remove_job(sub)
            logger.success(f"[scheduler] successfully removed subscription {sub}")
            return True
        else:
            return False

    async def unschedule_all_by_subscriber(self, subscriber: PostIdentifier[UID, GID]):
        old = await self.repo.delete_many_by_subscriber(subscriber)
        for sub in old:
            self._remove_job(sub)
            logger.success(f"[scheduler] successfully removed subscription {sub}")

    async def get_by_subscriber(self, subscriber: PostIdentifier[UID, GID]) -> List[Subscription]:
        return [x async for x in self.repo.get_by_subscriber(subscriber)]


__all__ = ("Scheduler",)

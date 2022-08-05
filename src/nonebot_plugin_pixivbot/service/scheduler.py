from __future__ import annotations

import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import TypeVar, Dict, List, Sequence, Union, Optional, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from lazy import lazy
from nonebot import logger, Bot

from nonebot_plugin_pixivbot.data.subscription_repo import SubscriptionRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect, on_bot_disconnect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler import Handler

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.inject
@context.register_eager_singleton()
class Scheduler:
    apscheduler: AsyncIOScheduler
    repo: SubscriptionRepo
    pd_factory_mgr: PostDestinationFactoryManager

    def __init__(self):
        on_bot_connect(self.on_bot_connect, replay=True)
        on_bot_disconnect(self.on_bot_disconnect)

    @staticmethod
    def _make_job_id(type: str, identifier: ID):
        if identifier.group_id:
            return f'{type} {identifier.adapter}:g{identifier.group_id}'
        else:
            return f'{type} {identifier.adapter}:u{identifier.user_id}'

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

    @lazy
    def _handlers(self) -> Dict[str, Handler]:
        # 解决Handler和Scheduler的循环引用
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler, RandomRecommendedIllustHandler, \
            RankingHandler, RandomIllustHandler, RandomUserIllustHandler
        return {
            RandomBookmarkHandler.type(): context.require(RandomBookmarkHandler),
            RandomRecommendedIllustHandler.type(): context.require(RandomRecommendedIllustHandler),
            RankingHandler.type(): context.require(RankingHandler),
            RandomIllustHandler.type(): context.require(RandomIllustHandler),
            RandomUserIllustHandler.type(): context.require(RandomUserIllustHandler),
        }

    async def _on_trigger(self, sub: Subscription[UID, GID], post_dest: PostDestination[UID, GID], silently: bool):
        job_id = self._make_job_id(sub.type, sub.identifier)
        logger.info(f"triggered {job_id}")
        await self._handlers[sub.type].handle(post_dest=post_dest, silently=silently, **sub.kwargs)

    def _add_job(self, post_dest: PostDestination[UID, GID], sub: Subscription[UID, GID]):
        offset_hour, offset_minute, hours, minutes = sub.schedule
        trigger = IntervalTrigger(hours=hours, minutes=minutes,
                                  start_date=datetime.now().replace(hour=offset_hour, minute=offset_minute,
                                                                    second=0, microsecond=0) + timedelta(days=-1))

        job_id = self._make_job_id(sub.type, sub.identifier)
        self.apscheduler.add_job(self._on_trigger, id=job_id, trigger=trigger,
                                 kwargs={"sub": sub, "post_dest": post_dest, "silently": True})
        logger.success(f"scheduled {job_id} {trigger}")

    def _remove_job(self, type: str, identifier: ID):
        job_id = self._make_job_id(type, identifier)
        self.apscheduler.remove_job(job_id)
        logger.success(f"unscheduled {job_id}")

    async def on_bot_connect(self, bot: Bot):
        adapter = get_adapter_name(bot)
        async for sub in self.repo.get_all(adapter):
            post_dest = self.pd_factory_mgr.build(
                bot, sub.user_id, sub.group_id)
            self._add_job(post_dest, sub)

    async def on_bot_disconnect(self, bot: Bot):
        async for subscription in self.repo.get_all(get_adapter_name(bot)):
            try:
                self._remove_job(subscription.type, subscription.identifier)
            except Exception as e:
                logger.error(
                    f"error occurred when remove job {self._make_job_id(subscription.type, subscription.identifier)}")
                logger.exception(e)

    async def schedule(self, type: str,
                       schedule: Union[str, Sequence[int]],
                       args: Optional[list] = None,
                       *, post_dest: PostDestination[UID, GID]):
        if type not in self._handlers:
            raise BadRequestError(f"{type}不是合法的类型")

        if args is None:
            args = []

        if isinstance(schedule, str):
            schedule = self._parse_schedule(schedule)

        kwargs = self._handlers[type].parse_args(args, post_dest)
        if isawaitable(kwargs):
            kwargs = await kwargs

        sub = Subscription(adapter=post_dest.adapter,
                           user_id=post_dest.user_id,
                           group_id=post_dest.group_id,
                           type=type,
                           schedule=schedule,
                           kwargs=kwargs)

        old_sub = await self.repo.update(sub)
        if old_sub is not None:
            self._remove_job(sub.type, sub.identifier)
        self._add_job(post_dest.normalized(), sub)

    async def unschedule(self, type: str,
                         identifier: PostIdentifier[UID, GID]):
        if type == "all":
            async for sub in self.repo.get(identifier):
                self._remove_job(sub.type, identifier)
        elif type in self._handlers:
            self._remove_job(type, identifier)
        else:
            raise BadRequestError(f"{type}不是合法的类型")

        await self.repo.delete(identifier, type)

    async def all_subscription(self, identifier: PostIdentifier[UID, GID]) -> List[Subscription]:
        return [x async for x in self.repo.get(identifier)]


__all__ = ("Scheduler",)

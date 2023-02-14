from __future__ import annotations

import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import Sequence, Union, TYPE_CHECKING, overload

import pytz
from apscheduler.triggers.interval import IntervalTrigger

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.subscription import SubscriptionRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model.subscription import ScheduleType
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.interval_task_worker import IntervalTaskWorker
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.nonebot import get_bot_user_identifier

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler


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


@context.register_eager_singleton()
@context.inject
class Scheduler(IntervalTaskWorker[Subscription[T_UID, T_GID]]):
    tag = "scheduler"
    repo: SubscriptionRepo = Inject(SubscriptionRepo)

    @classmethod
    def _get_handler(cls, type: ScheduleType) -> Handler:
        if type == ScheduleType.random_bookmark:
            from nonebot_plugin_pixivbot.handler.schedule import SubscriptionRandomBookmarkHandler
            return context.require(SubscriptionRandomBookmarkHandler)
        elif type == ScheduleType.random_recommended_illust:
            from nonebot_plugin_pixivbot.handler.schedule import SubscriptionRandomRecommendedIllustHandler
            return context.require(SubscriptionRandomRecommendedIllustHandler)
        elif type == ScheduleType.ranking:
            from nonebot_plugin_pixivbot.handler.schedule import SubscriptionRankingHandler
            return context.require(SubscriptionRankingHandler)
        elif type == ScheduleType.random_illust:
            from nonebot_plugin_pixivbot.handler.schedule import SubscriptionRandomIllustHandler
            return context.require(SubscriptionRandomIllustHandler)
        elif type == ScheduleType.random_user_illust:
            from nonebot_plugin_pixivbot.handler.schedule import SubscriptionRandomUserIllustHandler
            return context.require(SubscriptionRandomUserIllustHandler)

    async def _handle_trigger(self, sub: Subscription[T_UID, T_GID], post_dest: PostDestination[T_UID, T_GID]):
        await self._get_handler(sub.type).handle_with_parsed_args(post_dest=post_dest, silently=True, **sub.kwargs)

    def _make_job_trigger(self, item: Subscription[T_UID, T_GID]) -> IntervalTrigger:
        offset_hour, offset_minute, hours, minutes = item.schedule
        tz = pytz.timezone(item.tz)
        return IntervalTrigger(hours=hours, minutes=minutes,
                               start_date=datetime.now(tz).replace(hour=offset_hour,
                                                                   minute=offset_minute,
                                                                   second=0,
                                                                   microsecond=0) + timedelta(days=-1))

    async def _build_task(self, type_: ScheduleType,
                          schedule: Union[str, Sequence[int]],
                          args: Sequence[str],
                          post_dest: PostDestination[T_UID, T_GID]) -> Subscription[T_UID, T_GID]:
        if args is None:
            args = []

        if isinstance(schedule, str):
            schedule = parse_schedule(schedule)

        kwargs = self._get_handler(type_).parse_args(args, post_dest)
        if isawaitable(kwargs):
            kwargs = await kwargs

        bot = post_dest.bot
        sub = Subscription(type=type_, kwargs=kwargs,
                           subscriber=post_dest.identifier,
                           bot=get_bot_user_identifier(bot),
                           schedule=schedule)
        return sub

    @overload
    async def add_task(self, type_: ScheduleType,
                       schedule: Union[str, Sequence[int]],
                       args: Sequence[str],
                       post_dest: PostDestination[T_UID, T_GID]) -> bool:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        return await super().add_task(*args, **kwargs)


__all__ = ("Scheduler",)

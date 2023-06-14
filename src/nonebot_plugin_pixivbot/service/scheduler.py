from __future__ import annotations

import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import Sequence, Union, TYPE_CHECKING, overload, Type

import pytz
from apscheduler.triggers.interval import IntervalTrigger
from nonebot_plugin_session import Session

from .interval_task_worker import IntervalTaskWorker
from ..data.subscription import SubscriptionRepo
from ..global_context import context
from ..model import Subscription
from ..model.subscription import ScheduleType
from ..utils.errors import BadRequestError

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
class Scheduler(IntervalTaskWorker[Subscription]):
    tag = "scheduler"

    @property
    def repo(self) -> SubscriptionRepo:
        return context.require(SubscriptionRepo)

    @classmethod
    def _get_handler_type(cls, type: ScheduleType) -> Type["Handler"]:
        from ..handler.schedule import SubscriptionRandomBookmarkHandler, SubscriptionRandomRecommendedIllustHandler, \
            SubscriptionRankingHandler, SubscriptionRandomIllustHandler, SubscriptionRandomUserIllustHandler

        if type == ScheduleType.random_bookmark:
            return SubscriptionRandomBookmarkHandler
        elif type == ScheduleType.random_recommended_illust:
            return SubscriptionRandomRecommendedIllustHandler
        elif type == ScheduleType.ranking:
            return SubscriptionRankingHandler
        elif type == ScheduleType.random_illust:
            return SubscriptionRandomIllustHandler
        elif type == ScheduleType.random_user_illust:
            return SubscriptionRandomUserIllustHandler

    async def _handle_trigger(self, item: Subscription):
        handler_type = self._get_handler_type(item.type)
        await handler_type(item.subscriber, silently=True).handle_with_parsed_args(**item.kwargs)

    def _make_job_trigger(self, item: Subscription) -> IntervalTrigger:
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
                          session: Session) -> Subscription:
        if args is None:
            args = []

        if isinstance(schedule, str):
            schedule = parse_schedule(schedule)

        handler_type = self._get_handler_type(type_)
        kwargs = handler_type(session).parse_args(args)
        if isawaitable(kwargs):
            kwargs = await kwargs

        sub = Subscription(type=type_, kwargs=kwargs,
                           subscriber=session,
                           schedule=schedule)
        return sub

    @overload
    async def add_task(self, type_: ScheduleType,
                       schedule: Union[str, Sequence[int]],
                       args: Sequence[str],
                       session: Session) -> bool:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        return await super().add_task(*args, **kwargs)


__all__ = ("Scheduler",)

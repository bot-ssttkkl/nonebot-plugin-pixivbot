from __future__ import annotations

import re
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import Sequence, Union, TYPE_CHECKING, overload, Type, Optional

import pytz
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from nonebot_plugin_session import Session

from .interval_task_worker import IntervalTaskWorker
from ..data.subscription import SubscriptionRepo
from ..global_context import context
from ..model import Subscription
from ..model.subscription import ScheduleType, IntervalSchedule, CronSchedule
from ..utils.errors import BadRequestError

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler

# === interval schedule ===
reg_interval_schedule_start_only = re.compile(r'(\d+):(\d+)')
reg_interval_schedule_interval_only = re.compile(r'(\d+):(\d+)\*x')


def parse_interval_schedule(raw_schedule: str) -> Optional[IntervalSchedule]:
    start_only_mat = reg_interval_schedule_start_only.fullmatch(raw_schedule)
    if start_only_mat is not None:
        g = start_only_mat.groups()
        start_hour, start_minute = int(g[0]), int(g[1])
        if start_hour < 0 or start_hour >= 24 or start_minute < 0 or start_minute >= 60:
            raise BadRequestError(f'{raw_schedule}不是合法的时间')
        return IntervalSchedule(start_hour, start_minute, 24, 0)
    else:
        interval_only_mat = reg_interval_schedule_interval_only.fullmatch(raw_schedule)
        if interval_only_mat is not None:
            g = interval_only_mat.groups()
            interval_hour, interval_minute = int(g[0]), int(g[1])
            if interval_hour < 0 or interval_minute >= 60 \
                    or (interval_hour > 0 and interval_minute < 0) or (interval_hour == 0 and interval_minute <= 0):
                raise BadRequestError(f'{raw_schedule}不是合法的时间')
            return IntervalSchedule(0, 0, interval_hour, interval_minute)
        else:
            return None


# === cron schedule ===
# https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html?highlight=Cron#apscheduler.triggers.cron.CronTrigger
# don't ask me what these shit mean
cron_segment_patterns = [r"\d+", r"\*", r"\*/\d+", r"\d+-\d+", r"\d+-\d+/\d+"]
single_cron_segment_pattern = "|".join(f"({x})" for x in cron_segment_patterns)
union_cron_segment_pattern = f"^({single_cron_segment_pattern})(,({single_cron_segment_pattern}))*$"
reg_cron_segment = re.compile(union_cron_segment_pattern)

cron_day_segment_patterns = [*cron_segment_patterns, r"\d+th \d+", r"last \d+", r"last"]
single_cron_day_segment_pattern = "|".join(f"({x})" for x in cron_day_segment_patterns)
union_cron_day_segment_pattern = f"^({single_cron_day_segment_pattern})(,({single_cron_day_segment_pattern}))*$"
reg_cron_day_segment = re.compile(union_cron_day_segment_pattern)


def parse_cron_expression(cron: str) -> Optional[CronSchedule]:
    segments = cron.split(" ")  # second minute hour day month day_of_week
    if len(segments) != 6:
        return None

    if segments[3] == '?':
        segments[3] = '*'
    elif segments[5] == '?':
        segments[5] = '*'

    for i, seg in enumerate(segments):
        if reg_cron_segment.fullmatch(seg) is not None:
            continue
        elif i == 4 and reg_cron_day_segment.fullmatch(seg) is not None:
            continue
        raise BadRequestError(f'{cron}不是合法的时间')

    return CronSchedule(*segments)


def parse_schedule(raw_schedule: str) -> Union[IntervalSchedule, CronSchedule]:
    schedule = parse_interval_schedule(raw_schedule)
    if schedule is None:
        schedule = parse_cron_expression(raw_schedule)
    if schedule is None:
        raise BadRequestError(f'{raw_schedule}不是合法的时间')
    return schedule


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

    def _make_job_trigger(self, item: Subscription) -> BaseTrigger:
        if isinstance(item.schedule, IntervalSchedule):
            offset_hour, offset_minute, hours, minutes = item.schedule
            tz = pytz.timezone(item.tz)
            return IntervalTrigger(hours=hours, minutes=minutes,
                                   start_date=datetime.now(tz).replace(hour=offset_hour,
                                                                       minute=offset_minute,
                                                                       second=0,
                                                                       microsecond=0) + timedelta(days=-1))
        elif isinstance(item.schedule, CronSchedule):
            second, minute, hour, day, month, day_of_week = item.schedule
            return CronTrigger(month=month, day=day, day_of_week=day_of_week, hour=hour, minute=minute, second=second,
                               timezone=item.tz)
        else:
            raise TypeError(type(item.schedule))

    async def _build_task(self, type_: ScheduleType,
                          schedule: Union[str, Sequence[str]],
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
                       schedule: Union[str, Sequence[str]],
                       args: Sequence[str],
                       session: Session) -> bool:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        return await super().add_task(*args, **kwargs)


__all__ = ("Scheduler",)

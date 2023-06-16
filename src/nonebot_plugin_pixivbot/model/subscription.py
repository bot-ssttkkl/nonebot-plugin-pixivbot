from enum import Enum
from typing import Dict, Any, NamedTuple, Union

import tzlocal

from .interval_task import IntervalTask
from ..utils.format import format_kwargs


class ScheduleType(str, Enum):
    random_bookmark = "random_bookmark"
    random_recommended_illust = "random_recommended_illust"
    random_illust = "random_illust"
    random_user_illust = "random_user_illust"
    ranking = "ranking"


class IntervalSchedule(NamedTuple):
    start_hour: int
    start_minute: int
    interval_hours: int
    interval_minutes: int


class CronSchedule(NamedTuple):
    second: str
    minute: str
    hour: str
    day: str
    month: str
    day_of_week: str


class Subscription(IntervalTask):
    type: ScheduleType
    kwargs: Dict[str, Any]
    schedule: Union[IntervalSchedule, CronSchedule]
    tz: str = tzlocal.get_localzone_name()

    @property
    def schedule_text(self) -> str:
        if isinstance(self.schedule, IntervalSchedule):
            offset_hour, offset_minute, hours, minutes = self.schedule
            if hours == 24 and minutes == 0:
                return f'{str(offset_hour).zfill(2)}:{str(offset_minute).zfill(2)}'
            elif offset_hour == 0 and offset_minute == 0:
                return f'{str(hours).zfill(2)}:{str(minutes).zfill(2)}*x'
            else:
                return f'{str(offset_hour).zfill(2)}:{str(offset_minute).zfill(2)}' \
                       f'+{str(hours).zfill(2)}:{str(minutes).zfill(2)}*x'
        else:
            return " ".join(self.schedule)

    @property
    def args_text(self) -> str:
        filtered_kwargs = {}
        for k in self.kwargs:
            if self.kwargs[k]:
                filtered_kwargs[k] = self.kwargs[k]

        return format_kwargs(**filtered_kwargs)

    def __repr__(self):
        text = f'[{self.code}] {self.type} on {self.schedule_text} by {self.subscriber}'
        if len(self.kwargs) != 0:
            text += f' ({self.args_text})'
        return text

    def __str__(self):
        return self.__repr__()


__all__ = ("Subscription", "ScheduleType")

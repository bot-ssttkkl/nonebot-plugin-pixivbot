from enum import Enum
from typing import Sequence, Dict, Any, Generic

import tzlocal

from . import T_UID, T_GID
from .interval_task import IntervalTask
from ..utils.format import format_kwargs


class ScheduleType(str, Enum):
    random_bookmark = "random_bookmark"
    random_recommended_illust = "random_recommended_illust"
    random_illust = "random_illust"
    random_user_illust = "random_user_illust"
    ranking = "ranking"


class Subscription(IntervalTask[T_UID, T_GID], Generic[T_UID, T_GID]):
    type: ScheduleType
    kwargs: Dict[str, Any]
    schedule: Sequence[int]
    tz: str = tzlocal.get_localzone_name()

    @property
    def schedule_text(self) -> str:
        return f'{str(self.schedule[0]).zfill(2)}:{str(self.schedule[1]).zfill(2)}' \
               f'+{str(self.schedule[2]).zfill(2)}:{str(self.schedule[3]).zfill(2)}*x'

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

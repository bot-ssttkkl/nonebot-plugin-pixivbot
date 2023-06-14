from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from .interval_task import IntervalTask
from ..utils.format import format_kwargs


class WatchType(str, Enum):
    user_illusts = "user_illusts"
    following_illusts = "following_illusts"


class WatchTask(IntervalTask):
    type: WatchType
    kwargs: Dict[str, Any]
    checkpoint: datetime = datetime.now(timezone.utc)

    @property
    def args_text(self) -> str:
        filtered_kwargs = {}
        for k in self.kwargs:
            if self.kwargs[k]:
                filtered_kwargs[k] = self.kwargs[k]

        return format_kwargs(**filtered_kwargs)

    def __repr__(self):
        text = f'[{self.code}] {self.type} by {self.subscriber}'
        if len(self.kwargs) != 0:
            text += f' ({self.args_text})'
        return text

    def __str__(self):
        return self.__repr__()

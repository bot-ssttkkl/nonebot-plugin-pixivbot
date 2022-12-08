from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic

from . import T_UID, T_GID
from .interval_task import IntervalTask


class WatchType(str, Enum):
    user_illusts = "user_illusts"
    following_illusts = "following_illusts"


class WatchTask(IntervalTask[T_UID, T_GID], Generic[T_UID, T_GID]):
    type: WatchType
    kwargs: Dict[str, Any]
    checkpoint: datetime = datetime.now(timezone.utc)

    @property
    def args_text(self) -> str:
        args = list(filter(lambda kv: kv[1], self.kwargs.items()))
        if len(args) != 0:
            return ", ".join(map(lambda kv: f'{kv[0]}={kv[1]}', args))
        else:
            return ""

    def __repr__(self):
        text = f'[{self.code}] {self.type} by {self.subscriber}'
        if len(self.kwargs) != 0:
            text += f' ({self.args_text})'
        return text

    def __str__(self):
        return self.__repr__()


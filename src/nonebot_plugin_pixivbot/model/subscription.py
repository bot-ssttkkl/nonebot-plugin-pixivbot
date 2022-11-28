from enum import Enum
from typing import Generic, Sequence, Dict, Any

import tzlocal
from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import PostIdentifier, T_UID, T_GID


class ScheduleType(str, Enum):
    random_bookmark = "random_bookmark"
    random_recommended_illust = "random_recommended_illust"
    random_illust = "random_illust"
    random_user_illust = "random_user_illust"
    ranking = "ranking"


class Subscription(GenericModel, Generic[T_UID, T_GID]):
    code: str = ""
    type: ScheduleType
    kwargs: Dict[str, Any]
    subscriber: PostIdentifier[T_UID, T_GID]
    schedule: Sequence[int]
    tz: str = tzlocal.get_localzone_name()

    @property
    def schedule_text(self) -> str:
        return f'{str(self.schedule[0]).zfill(2)}:{str(self.schedule[1]).zfill(2)}' \
               f'+{str(self.schedule[2]).zfill(2)}:{str(self.schedule[3]).zfill(2)}*x'

    @property
    def args_text(self) -> str:
        args = list(filter(lambda kv: kv[1], self.kwargs.items()))
        if len(args) != 0:
            return ", ".join(map(lambda kv: f'{kv[0]}={kv[1]}', args))
        else:
            return ""

    def __repr__(self):
        text = f'[{self.code}] {self.type} on {self.schedule_text} by {self.subscriber}'
        if len(self.kwargs) != 0:
            text += f' ({self.args_text})'
        return text

    def __str__(self):
        return self.__repr__()

    class Config:
        orm_mode = True


__all__ = ("Subscription", "ScheduleType")

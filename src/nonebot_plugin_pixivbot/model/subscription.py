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

    class Config:
        orm_mode = True


__all__ = ("Subscription", "ScheduleType")

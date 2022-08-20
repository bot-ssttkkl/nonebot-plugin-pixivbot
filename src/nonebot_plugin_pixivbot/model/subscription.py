from enum import Enum
from typing import TypeVar, Generic, Sequence, Dict, Any

import tzlocal
from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")


class ScheduleType(Enum):
    random_bookmark = "random_bookmark"
    random_recommended_illust = "random_recommended_illust"
    random_illust = "random_illust"
    random_user_illust = "random_user_illust"
    ranking = "ranking"


class Subscription(GenericModel, Generic[UID, GID]):
    type: ScheduleType
    kwargs: Dict[str, Any]
    subscriber: PostIdentifier[UID, GID]
    schedule: Sequence[int]
    tz: str = tzlocal.get_localzone_name()


__all__ = ("Subscription", "ScheduleType")

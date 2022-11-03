from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Dict

from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.model import T_UID, T_GID


class WatchType(str, Enum):
    user_illusts = "user_illusts"
    following_illusts = "following_illusts"


class WatchTask(GenericModel, Generic[T_UID, T_GID]):
    code: str = ""
    type: WatchType
    kwargs: Dict[str, Any]
    subscriber: PostIdentifier[T_UID, T_GID]
    checkpoint: datetime = datetime.now(timezone.utc)

    class Config:
        orm_mode = True

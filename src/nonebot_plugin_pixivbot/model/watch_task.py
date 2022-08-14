from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeVar, Generic, Dict

from pydantic import BaseModel

from nonebot_plugin_pixivbot.model import PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")


class WatchType(Enum):
    user_illusts = "user_illusts"
    following_illusts = "following_illusts"


class WatchTask(BaseModel, Generic[UID, GID]):
    type: WatchType
    kwargs: Dict[str, Any]
    subscriber: PostIdentifier[UID, GID]
    checkpoint: datetime = datetime.now(timezone.utc)

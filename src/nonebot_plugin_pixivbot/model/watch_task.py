from datetime import datetime, timezone
from typing import Any, TypeVar, Generic, Dict

from pydantic import BaseModel

from nonebot_plugin_pixivbot.model import PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")


class WatchTask(BaseModel, Generic[UID, GID]):
    type: str
    args: Dict[str, Any]
    subscriber: PostIdentifier[UID, GID]
    checkpoint: datetime = datetime.now(timezone.utc)

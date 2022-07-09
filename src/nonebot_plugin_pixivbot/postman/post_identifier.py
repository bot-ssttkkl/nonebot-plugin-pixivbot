from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

UID = TypeVar("UID")
GID = TypeVar("GID")


@dataclass(frozen=True)
class PostIdentifier(Generic[UID, GID]):
    user_id: Optional[UID]
    group_id: Optional[GID]

    def __post_init__(self):
        if not self.user_id and not self.group_id:
            raise ValueError("at least one of user_id and group_id should be not None")

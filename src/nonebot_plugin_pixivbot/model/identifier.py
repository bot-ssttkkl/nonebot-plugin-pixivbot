from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

UID = TypeVar("UID")
GID = TypeVar("GID")


@dataclass(frozen=True)
class UserIdentifier(Generic[UID]):
    adapter: str
    user_id: UID

    def __str__(self):
        return f"{self.adapter}:{self.user_id}"


@dataclass(frozen=True)
class PostIdentifier(Generic[UID, GID]):
    adapter: str
    user_id: Optional[UID]
    group_id: Optional[GID]

    def __str__(self):
        return f"{self.adapter}:{self.user_id}:{self.group_id}"

    def __post_init__(self):
        if not self.user_id and not self.group_id:
            raise ValueError("at least one of user_id and group_id should be not None")

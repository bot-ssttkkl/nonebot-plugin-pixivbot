from typing import TypeVar, Generic, Optional

from pydantic import root_validator
from pydantic.generics import GenericModel

UID = TypeVar("UID")
GID = TypeVar("GID")


class UserIdentifier(GenericModel, Generic[UID]):
    adapter: str
    user_id: UID

    def __init__(self, adapter: str, user_id: UID):
        super().__init__(adapter=adapter, user_id=user_id)

    def __str__(self):
        return f"{self.adapter}:{self.user_id}"

    class Config:
        frozen = True


class PostIdentifier(GenericModel, Generic[UID, GID]):
    adapter: str
    user_id: Optional[UID]
    group_id: Optional[GID]

    def __init__(self, adapter: str, user_id: Optional[UID] = None, group_id: Optional[GID] = None):
        super().__init__(adapter=adapter, user_id=user_id, group_id=group_id)

    def __str__(self):
        return f"{self.adapter}:{self.user_id}:{self.group_id}"

    @root_validator(allow_reuse=True)
    def validator(cls, values):
        if not values.get("user_id", None) and not values.get("group_id", None):
            raise ValueError("at least one of user_id and group_id should not be None")
        return values

    class Config:
        frozen = True

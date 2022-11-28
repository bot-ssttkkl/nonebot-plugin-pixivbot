from typing import TypeVar, Generic, Optional

from pydantic import root_validator
from pydantic.generics import GenericModel

T_UID = TypeVar("T_UID")
T_GID = TypeVar("T_GID")


class UserIdentifier(GenericModel, Generic[T_UID]):
    adapter: str
    user_id: T_UID

    def __init__(self, adapter: str, user_id: T_UID):
        super().__init__(adapter=adapter, user_id=user_id)

    def __repr__(self):
        return f"{self.adapter}:{self.user_id}"

    class Config:
        frozen = True


class PostIdentifier(GenericModel, Generic[T_UID, T_GID]):
    adapter: str
    user_id: Optional[T_UID]
    group_id: Optional[T_GID]

    def __init__(self, adapter: str, user_id: Optional[T_UID] = None, group_id: Optional[T_GID] = None):
        super().__init__(adapter=adapter, user_id=user_id, group_id=group_id)

    def __repr__(self):
        return f"{self.adapter}:{self.user_id}:{self.group_id}"

    def __str__(self):
        return self.__repr__()

    @root_validator(allow_reuse=True)
    def validator(cls, values):
        if not values.get("user_id", None) and not values.get("group_id", None):
            raise ValueError("at least one of user_id and group_id should not be None")
        return values

    class Config:
        frozen = True

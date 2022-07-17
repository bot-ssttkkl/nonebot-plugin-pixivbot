from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

from nonebot.internal.adapter import Event

UID = TypeVar("UID")
GID = TypeVar("GID")


class PostDestination(ABC, Generic[UID, GID]):

    @property
    def adapter(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def user_id(self) -> Optional[UID]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def group_id(self) -> Optional[GID]:
        raise NotImplementedError()


class PostDestinationFactory(ABC, Generic[UID, GID]):
    @abstractmethod
    def build(self, user_id: Optional[UID], group_id: Optional[GID]) -> PostDestination:
        raise NotImplementedError()

    @abstractmethod
    def from_event(self, event: Event) -> PostDestination:
        raise NotImplementedError()

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

UID = TypeVar("UID")
GID = TypeVar("GID")


class PostDestination(ABC, Generic[UID, GID]):

    @property
    def adapter(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def user_id(self) -> UID:
        raise NotImplementedError()

    @property
    @abstractmethod
    def group_id(self) -> GID:
        raise NotImplementedError()


class PostDestinationFactory(ABC, Generic[UID, GID]):
    @abstractmethod
    def build(self, user_id: UID, group_id: GID) -> PostDestination:
        raise NotImplementedError()

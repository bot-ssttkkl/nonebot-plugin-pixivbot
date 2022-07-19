from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Type, Dict
from nonebot import Bot

from nonebot.internal.adapter import Event

from nonebot_plugin_pixivbot.global_context import context

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
    @classmethod
    @abstractmethod
    def adapter(cls) -> str:
        raise NotImplementedError()

    @abstractmethod
    def build(self, bot: Bot, user_id: Optional[UID], group_id: Optional[GID]) -> PostDestination:
        raise NotImplementedError()

    @abstractmethod
    def from_event(self, bot: Bot, event: Event) -> PostDestination:
        raise NotImplementedError()


@context.register_singleton()
class PostDestinationFactoryManager:
    def __init__(self):
        self.factories: Dict[str, Type[PostDestinationFactory]] = {}

    def register(self, cls: Type[PostDestinationFactory]):
        self.factories[cls.adapter()] = cls
        if cls not in context:
            context.register_singleton()(cls)
        return cls

    def require(self, adapter: str):
        return context.require(self.factories[adapter])

    def __getitem__(self, adapter: str):
        return self.require(adapter)

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Type, Dict

from nonebot import Bot
from nonebot.internal.adapter import Event

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model.identifier import PostIdentifier
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

UID = TypeVar("UID")
GID = TypeVar("GID")


class PostDestination(ABC, Generic[UID, GID]):

    @property
    @abstractmethod
    def identifier(self) -> PostIdentifier:
        raise NotImplementedError()

    @property
    def adapter(self) -> str:
        return self.identifier.adapter

    @property
    def user_id(self) -> Optional[UID]:
        return self.identifier.user_id

    @property
    def group_id(self) -> Optional[GID]:
        return self.identifier.group_id

    def __str__(self) -> str:
        return str(self.identifier)

    @abstractmethod
    def normalized(self) -> "PostDestination[UID, GID]":
        """
        返回一个不含任何附加信息（如引用消息）的PostDestination
        :return:
        """
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

    def build(self, bot: Bot, user_id: Optional[UID], group_id: Optional[GID]) -> PostDestination:
        return self[get_adapter_name(bot)].build(bot, user_id, group_id)

    def from_event(self, bot: Bot, event: Event) -> PostDestination:
        return self[get_adapter_name(bot)].from_event(bot, event)

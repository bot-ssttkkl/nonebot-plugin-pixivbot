from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

from nonebot import Bot
from nonebot.internal.adapter import Event

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model.identifier import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

UID = TypeVar("UID")
GID = TypeVar("GID")


class PostDestination(ABC, Generic[UID, GID]):

    @property
    @abstractmethod
    def identifier(self) -> PostIdentifier[UID, GID]:
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


class PostDestinationFactory(ProtocolDep, ABC, Generic[UID, GID]):
    @abstractmethod
    def build(self, bot: Bot, user_id: Optional[UID], group_id: Optional[GID]) -> PostDestination:
        raise NotImplementedError()

    @abstractmethod
    def from_event(self, bot: Bot, event: Event) -> PostDestination:
        raise NotImplementedError()


@context.register_singleton()
class PostDestinationFactoryManager(ProtocolDepManager[PostDestinationFactory]):
    def build(self, bot: Bot, user_id: Optional[UID], group_id: Optional[GID]) -> PostDestination[UID, GID]:
        return self[get_adapter_name(bot)].build(bot, user_id, group_id)

    def from_event(self, bot: Bot, event: Event) -> PostDestination[UID, GID]:
        return self[get_adapter_name(bot)].from_event(bot, event)


__all__ = ("PostDestination", "PostDestinationFactory", "PostDestinationFactoryManager")

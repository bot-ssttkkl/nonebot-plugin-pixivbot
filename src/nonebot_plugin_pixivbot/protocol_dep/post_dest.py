from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import Generic, Optional

from nonebot import Bot
from nonebot.internal.adapter import Event

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model.identifier import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name


class PostDestination(ABC, Generic[T_UID, T_GID]):

    @property
    @abstractmethod
    def identifier(self) -> PostIdentifier[T_UID, T_GID]:
        raise NotImplementedError()

    @property
    def adapter(self) -> str:
        return self.identifier.adapter

    @property
    def user_id(self) -> Optional[T_UID]:
        return self.identifier.user_id

    @property
    def group_id(self) -> Optional[T_GID]:
        return self.identifier.group_id

    def __str__(self) -> str:
        return str(self.identifier)

    @abstractmethod
    def normalized(self) -> "PostDestination[T_UID, T_GID]":
        """
        返回一个不含任何附加信息（如引用消息）的PostDestination
        :return:
        """
        raise NotImplementedError()


current_post_dest: ContextVar[PostDestination[T_UID, T_GID]] = ContextVar("current_post_dest")


class PostDestinationFactory(ProtocolDep, ABC, Generic[T_UID, T_GID]):
    @abstractmethod
    def build(self, bot: Bot, user_id: Optional[T_UID], group_id: Optional[T_GID]) -> PostDestination:
        raise NotImplementedError()

    @abstractmethod
    def from_event(self, bot: Bot, event: Event) -> PostDestination:
        raise NotImplementedError()


@context.register_singleton()
class PostDestinationFactoryManager(ProtocolDepManager[PostDestinationFactory]):
    def build(self, bot: Bot, user_id: Optional[T_UID], group_id: Optional[T_GID]) -> PostDestination[T_UID, T_GID]:
        return self[get_adapter_name(bot)].build(bot, user_id, group_id)

    def from_event(self, bot: Bot, event: Event) -> PostDestination[T_UID, T_GID]:
        return self[get_adapter_name(bot)].from_event(bot, event)


__all__ = ("PostDestination", "PostDestinationFactory", "PostDestinationFactoryManager",
           "current_post_dest")

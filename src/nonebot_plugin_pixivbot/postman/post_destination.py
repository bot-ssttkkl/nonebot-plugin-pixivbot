from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.postman.post_identifier import PostIdentifier
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class PostDestination(ABC, Generic[UID, GID, B, M]):
    def __init__(self, bot: B, user_id: UID, group_id: GID):
        self.bot = bot
        self.identifier = PostIdentifier(get_adapter_name(bot), user_id, group_id)

    @property
    def user_id(self) -> UID:
        return self.identifier.user_id

    @property
    def group_id(self) -> GID:
        return self.identifier.group_id

    @abstractmethod
    async def post(self, message: M):
        raise NotImplementedError()


class PostDestinationFactory(ABC, Generic[UID, GID, B, M]):
    @abstractmethod
    def from_id(self, bot: B, user_id: UID, group_id: GID) -> PostDestination[UID, GID, B, M]:
        raise NotImplementedError

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.postman.post_identifier import PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class PostDestination(ABC, Generic[UID, GID, B, M]):
    def __init__(self, bot: B, identifier: PostIdentifier[UID, GID]):
        self.bot = bot
        self.identifier = identifier

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
    def from_id(self, bot: B, identifier: PostIdentifier[UID, GID]) -> PostDestination[UID, GID, B, M]:
        raise NotImplementedError

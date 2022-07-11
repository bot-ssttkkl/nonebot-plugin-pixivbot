from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Sequence

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.postman.model.illust_message import IllustMessageModel
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class Postman(ABC, Generic[UID, GID, B, M]):
    @abstractmethod
    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, message: IllustMessageModel,
                          *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, message: Sequence[IllustMessageModel],
                           *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()


__all__ = ("Postman",)

from abc import ABC, abstractmethod
from typing import TypeVar

from nonebot_plugin_pixivbot.postman.model import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class Postman(ABC):
    @abstractmethod
    async def send_plain_text(self, message: str,
                              *, post_dest: PD):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PD):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PD):
        raise NotImplementedError()


__all__ = ("Postman",)

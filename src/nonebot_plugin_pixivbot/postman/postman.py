from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from nonebot_plugin_pixivbot.postman.model import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


class Postman(ABC, Generic[UID, GID]):
    @abstractmethod
    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination[UID, GID]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination[UID, GID]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination[UID, GID]):
        raise NotImplementedError()


__all__ = ("Postman",)

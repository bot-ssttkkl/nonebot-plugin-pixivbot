from abc import ABC, abstractmethod
from typing import Union, Optional, Generic, TypeVar, Sequence

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class Postman(ABC, Generic[UID, GID, B, M]):
    @abstractmethod
    async def send_message(self, message: Union[str, M],
                           *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, illust: Illust,
                          header: Union[str, M, None] = None,
                          number: Optional[int] = None,
                          *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, illusts: Sequence[Illust],
                           header: Union[str, M, None] = None,
                           number: Optional[int] = None,
                           *, post_dest: PostDestination[UID, GID, B, M]):
        raise NotImplementedError()


__all__ = ("Postman",)

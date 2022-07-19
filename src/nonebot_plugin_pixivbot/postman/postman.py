from abc import ABC, abstractmethod
from typing import TypeVar, Dict, Type, Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman.model import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class Postman(ABC, Generic[UID, GID]):
    @classmethod
    @abstractmethod
    def adapter(cls) -> str:
        raise NotImplementedError()

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


@context.register_singleton()
class PostmanManager:
    def __init__(self):
        self.postmen: Dict[str, Type[Postman]] = {}

    def register(self, cls: Type[Postman]):
        self.postmen[cls.adapter()] = cls
        if cls not in context:
            context.register_singleton()(cls)
        return cls

    def require(self, adapter: str):
        return context.require(self.postmen[adapter])

    def __getitem__(self, adapter: str):
        return self.require(adapter)

    async def send_plain_text(self, message: str,
                              *, post_dest: PD):
        return await self[post_dest.adapter].send_plain_text(message, post_dest=post_dest)

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PD):
        return await self[post_dest.adapter].send_illust(model, post_dest=post_dest)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PD):
        return await self[post_dest.adapter].send_illusts(model, post_dest=post_dest)


__all__ = ("Postman", "PostmanManager")

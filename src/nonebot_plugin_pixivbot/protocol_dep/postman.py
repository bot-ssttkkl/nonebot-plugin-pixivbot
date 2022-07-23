from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class Postman(ProtocolDep, ABC, Generic[UID, GID]):
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
class PostmanManager(ProtocolDepManager[Postman]):
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

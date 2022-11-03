from abc import ABC, abstractmethod
from typing import Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager


class Postman(ProtocolDep, ABC, Generic[T_UID, T_GID]):
    @abstractmethod
    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination[T_UID, T_GID]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination[T_UID, T_GID]):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination[T_UID, T_GID]):
        raise NotImplementedError()


@context.register_singleton()
class PostmanManager(ProtocolDepManager[Postman]):
    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination[T_UID, T_GID]):
        return await self[post_dest.adapter].send_plain_text(message, post_dest=post_dest)

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination[T_UID, T_GID]):
        return await self[post_dest.adapter].send_illust(model, post_dest=post_dest)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination[T_UID, T_GID]):
        return await self[post_dest.adapter].send_illusts(model, post_dest=post_dest)


__all__ = ("Postman", "PostmanManager")

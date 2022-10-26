from abc import ABC, abstractmethod
from typing import TypeVar, Union, Awaitable, Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager

UID = TypeVar("UID")
GID = TypeVar("GID")


class Authenticator(ProtocolDep, ABC, Generic[UID, GID]):
    @abstractmethod
    def group_admin(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()

    @abstractmethod
    def available(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()


@context.register_singleton()
class AuthenticatorManager(ProtocolDepManager[Authenticator]):
    def group_admin(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        return self[post_dest.adapter].group_admin(post_dest)

    def available(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        return self[post_dest.adapter].available(post_dest)


__all__ = ("Authenticator", "AuthenticatorManager")

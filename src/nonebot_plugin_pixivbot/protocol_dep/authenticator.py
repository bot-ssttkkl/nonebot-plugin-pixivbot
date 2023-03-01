from abc import ABC, abstractmethod
from typing import Union, Awaitable, Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.protocol_dep import ProtocolDep, ProtocolDepManager


class Authenticator(ProtocolDep, ABC, Generic[T_UID, T_GID]):
    @abstractmethod
    def available(self, post_dest: PostDestination[T_UID, T_GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()


@context.register_singleton()
class AuthenticatorManager(ProtocolDepManager[Authenticator]):
    def available(self, post_dest: PostDestination[T_UID, T_GID]) -> Union[bool, Awaitable[bool]]:
        return self[post_dest.adapter].available(post_dest)


__all__ = ("Authenticator", "AuthenticatorManager")

from abc import ABC, abstractmethod
from typing import TypeVar, Union, Awaitable, Dict, Type

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


class Authenticator(ABC):
    @classmethod
    @abstractmethod
    def adapter(cls) -> str:
        raise NotImplementedError()

    @abstractmethod
    def group_admin(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()


@context.register_singleton()
class AuthenticatorManager:
    def __init__(self):
        self.factories: Dict[str, Type[Authenticator]] = {}

    def register(self, cls: Type[Authenticator]):
        self.factories[cls.adapter()] = cls
        if cls not in context:
            context.register_singleton()(cls)
        return cls

    def require(self, adapter: str):
        return context.require(self.factories[adapter])

    def __getitem__(self, adapter: str):
        return self.require(adapter)

    def group_admin(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        return self[post_dest.adapter].group_admin(post_dest)

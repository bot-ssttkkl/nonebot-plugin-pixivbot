from abc import ABC, abstractmethod
from typing import TypeVar, Union, Awaitable

from nonebot_plugin_pixivbot.postman import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


class UserAuthenticator(ABC):
    @abstractmethod
    def group_admin(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()

from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import TypeVar, Callable, Generic, Union, Awaitable, Optional

from nonebot import get_driver, logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.user_authenticator import UserAuthenticator
from .interceptor import Interceptor
from ..utils import post_plain_text

UID = TypeVar("UID")
GID = TypeVar("GID")


class PermissionInterceptor(Interceptor[UID, GID], ABC, Generic[UID, GID]):

    @abstractmethod
    def has_permission(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()

    def get_permission_denied_msg(self, post_dest: PostDestination[UID, GID]) \
            -> Union[Optional[str], Awaitable[Optional[str]]]:
        return None

    async def actual_intercept(self, wrapped_func: Callable, *,
                               post_dest: PostDestination[UID, GID],
                               silently: bool,
                               **kwargs):
        p = self.has_permission(post_dest)
        if isawaitable(p):
            p = await p

        if p:
            await wrapped_func(post_dest=post_dest, silently=silently, **kwargs)
        else:
            logger.debug(f"permission denied {post_dest}")
            if not silently:
                msg = self.get_permission_denied_msg(post_dest)
                if isawaitable(msg):
                    await msg
                if msg:
                    await post_plain_text(msg, post_dest=post_dest)


class AnyPermissionInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def __init__(self, *interceptors: PermissionInterceptor):
        self.interceptors = list(interceptors)

    def append(self, interceptor: PermissionInterceptor):
        self.interceptors.append(interceptor)

    async def has_permission(self, post_dest: PostDestination[UID, GID]) -> bool:
        for inter in self.interceptors:
            p = inter.has_permission(post_dest)
            if isawaitable(p):
                p = await p

            if p:
                return True

        return False


class AllPermissionInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def __init__(self, *interceptors: PermissionInterceptor):
        self.interceptors = list(interceptors)

    def append(self, interceptor: PermissionInterceptor):
        self.interceptors.append(interceptor)

    async def has_permission(self, post_dest: PostDestination[UID, GID]) -> bool:
        for inter in self.interceptors:
            p = inter.has_permission(post_dest)
            if isawaitable(p):
                p = await p

            if not p:
                return False

        return True


@context.register_singleton()
class SuperuserInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def __init__(self):
        self.superusers = get_driver().config.superusers.copy()

    def has_permission(self, post_dest: PostDestination[UID, GID]) -> bool:
        return str(post_dest.user_id) in self.superusers \
               or f"{post_dest.adapter}:{post_dest.user_id}" in self.superusers


@context.register_singleton()
class GroupAdminInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def has_permission(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        if not post_dest.group_id:
            return True
        auth = context.require(UserAuthenticator)
        return auth.group_admin(post_dest)


@context.register_singleton()
class BlacklistInterceptor(PermissionInterceptor[UID, GID], Generic[UID, GID]):
    def __init__(self):
        self.blacklist = context.require(Config).blacklist

    def has_permission(self, post_dest: PostDestination[UID, GID]) -> bool:
        return str(post_dest.user_id) not in self.blacklist \
               and f"{post_dest.adapter}:{post_dest.user_id}" not in self.blacklist

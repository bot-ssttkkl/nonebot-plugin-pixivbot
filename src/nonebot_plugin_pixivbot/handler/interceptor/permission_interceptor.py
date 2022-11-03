from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Callable, Union, Awaitable, Optional

from nonebot import get_driver, logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import Interceptor
from ..pkg_context import context


class PermissionInterceptor(Interceptor, ABC):
    @abstractmethod
    def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> Union[bool, Awaitable[bool]]:
        raise NotImplementedError()

    def get_permission_denied_msg(self, post_dest: PostDestination[T_UID, T_GID]) \
            -> Union[Optional[str], Awaitable[Optional[str]]]:
        return None

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        p = self.has_permission(post_dest)
        if isawaitable(p):
            p = await p

        if p:
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        else:
            logger.debug(f"permission denied {post_dest}")
            if not silently:
                msg = self.get_permission_denied_msg(post_dest)
                if isawaitable(msg):
                    await msg
                if msg:
                    await self.post_plain_text(msg, post_dest=post_dest)


class AnyPermissionInterceptor(PermissionInterceptor):
    def __init__(self, *interceptors: PermissionInterceptor):
        super().__init__()
        self.interceptors = list(interceptors)

    def append(self, interceptor: PermissionInterceptor):
        self.interceptors.append(interceptor)

    async def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        for inter in self.interceptors:
            p = inter.has_permission(post_dest)
            if isawaitable(p):
                p = await p

            if p:
                return True

        return False


@context.register_singleton()
class SuperuserInterceptor(PermissionInterceptor):
    def __init__(self):
        super().__init__()
        self.superusers = get_driver().config.superusers

    def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        return str(post_dest.user_id) in self.superusers \
               or f"{post_dest.adapter}:{post_dest.user_id}" in self.superusers


@context.inject
@context.register_singleton()
class GroupAdminInterceptor(PermissionInterceptor):
    auth = Inject(AuthenticatorManager)

    def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> Union[bool, Awaitable[bool]]:
        if not post_dest.group_id:
            return True
        return self.auth.group_admin(post_dest)


@context.inject
@context.register_singleton()
class BlacklistInterceptor(PermissionInterceptor):
    conf = Inject(Config)

    def __init__(self):
        super().__init__()
        self.blacklist = self.conf.blacklist

    def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        return str(post_dest.user_id) not in self.blacklist \
               and f"{post_dest.adapter}:{post_dest.user_id}" not in self.blacklist

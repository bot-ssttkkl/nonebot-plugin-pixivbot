from abc import ABC, abstractmethod
from typing import Callable, Optional, TYPE_CHECKING

from nonebot import get_driver, logger

from .base import Interceptor
from ..pkg_context import context

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler


class PermissionInterceptor(Interceptor, ABC):
    @abstractmethod
    async def has_permission(self, handler: "Handler") -> bool:
        raise NotImplementedError()

    async def get_permission_denied_msg(self, handler: "Handler") -> Optional[str]:
        return None

    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        p = await self.has_permission(handler)

        if p:
            await wrapped_func(*args, **kwargs)
        else:
            logger.debug(f"permission denied {handler.post_dest}")
            if not handler.silently:
                msg = await self.get_permission_denied_msg(handler)
                if msg:
                    await handler.post_plain_text(msg)


class AnyPermissionInterceptor(PermissionInterceptor):
    def __init__(self, *interceptors: PermissionInterceptor):
        super().__init__()
        self.interceptors = list(interceptors)

    def append(self, interceptor: PermissionInterceptor):
        self.interceptors.append(interceptor)

    async def has_permission(self, handler: "Handler") -> bool:
        for inter in self.interceptors:
            p = await inter.has_permission(handler)
            if p:
                return True

        return False


@context.register_singleton()
class SuperuserInterceptor(PermissionInterceptor):
    async def has_permission(self, handler: "Handler") -> bool:
        superusers = get_driver().config.superusers
        return str(handler.post_dest.user_id) in superusers \
               or f"{handler.post_dest.adapter}:{handler.post_dest.user_id}" in superusers

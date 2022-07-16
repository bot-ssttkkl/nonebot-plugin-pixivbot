from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, TypeVar, Generic, Sequence, Any, Optional

from lazy import lazy

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.interceptor.combined_interceptor import CombinedInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import PermissionInterceptor
from nonebot_plugin_pixivbot.postman import Postman
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")


class Handler(ABC, Generic[UID, GID]):
    conf = context.require(Config)

    def __init__(self, interceptor: Optional[Interceptor[UID, GID]] = None):
        self.interceptor = interceptor

        self.permission_interceptor_delegation = PermissionInterceptorDelegation()
        self.add_interceptor(self.permission_interceptor_delegation)

    @lazy
    def postman(self):
        return context.require(Postman)

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def enabled(cls) -> bool:
        raise NotImplementedError()

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> Union[dict, Awaitable[dict]]:
        """
        将位置参数转化为命名参数
        :param args: 位置参数sequence
        :param post_dest: PostDestination
        :return: 命名参数dict
        """
        return {}

    async def handle(self, *args,
                     post_dest: PostDestination[UID, GID],
                     silently: bool = False,
                     **kwargs):
        try:
            parsed_kwargs = self.parse_args(args, post_dest)
            if isawaitable(parsed_kwargs):
                parsed_kwargs = await parsed_kwargs
        except:
            raise BadRequestError("参数错误")

        kwargs = {**kwargs, **parsed_kwargs}

        if self.interceptor is not None:
            await self.interceptor.intercept(self.actual_handle,
                                             post_dest=post_dest, silently=silently,
                                             **kwargs)
        else:
            await self.actual_handle(post_dest=post_dest, silently=silently, **kwargs)

    @abstractmethod
    async def actual_handle(self, *, post_dest: PostDestination[UID, GID],
                            silently: bool = False, **kwargs):
        """
        处理指令
        :param post_dest: PostDestination
        :param silently: 失败时不发送消息
        :param kwargs: 参数dict
        """
        raise NotImplementedError()

    def add_interceptor(self, interceptor: Interceptor[UID, GID]):
        if self.interceptor:
            self.interceptor = CombinedInterceptor(self.interceptor, interceptor)
        else:
            self.interceptor = interceptor

    def get_permission_interceptor(self):
        return self.permission_interceptor_delegation.delegation

    def set_permission_interceptor(self, interceptor: PermissionInterceptor[UID, GID]):
        self.permission_interceptor_delegation.delegation = interceptor


class PermissionInterceptorDelegation(PermissionInterceptor, Generic[UID, GID]):
    def __init__(self):
        self.delegation = None

    def has_permission(self, post_dest: PostDestination[UID, GID]) -> Union[bool, Awaitable[bool]]:
        if self.delegation:
            return self.delegation.has_permission(post_dest)
        else:
            return True

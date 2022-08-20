from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, TypeVar, Sequence

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .interceptor.combined_interceptor import CombinedInterceptor
from .interceptor.interceptor import Interceptor
from ..protocol_dep.postman import PostmanManager

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


@context.inject
class Handler(ABC):
    conf: Config
    postman_manager: PostmanManager

    def __init__(self):
        self.interceptor = None

    async def post_plain_text(self, message: str,
                              post_dest: PostDestination):
        await self.postman_manager.send_plain_text(message, post_dest=post_dest)

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError()

    def parse_args(self, args: Sequence[str], post_dest: PD) -> Union[dict, Awaitable[dict]]:
        """
        将位置参数转化为命名参数
        :param args: 位置参数sequence
        :param post_dest: PostDestination
        :return: 命名参数dict
        """
        return {}

    async def handle(self, *args,
                     post_dest: PD,
                     silently: bool = False,
                     disabled_interceptors: bool = False,
                     **kwargs):
        if not self.enabled():
            return

        if self.interceptor is not None and not disabled_interceptors:
            await self.interceptor.intercept(self.handle_with_args, *args,
                                             post_dest=post_dest,
                                             silently=silently,
                                             **kwargs)
        else:
            await self.handle_with_args(*args, post_dest=post_dest, silently=silently, **kwargs)

    async def handle_with_args(self, *args,
                               post_dest: PD,
                               silently: bool = False,
                               **kwargs):
        parsed_kwargs = self.parse_args(args, post_dest)
        if isawaitable(parsed_kwargs):
            parsed_kwargs = await parsed_kwargs

        kwargs = {**kwargs, **parsed_kwargs}
        await self.actual_handle(post_dest=post_dest, silently=silently, **kwargs)

    @abstractmethod
    async def actual_handle(self, *, post_dest: PD,
                            silently: bool = False,
                            **kwargs):
        """
        处理指令
        :param post_dest: PostDestination
        :param silently: 失败时不发送消息
        :param kwargs: 参数dict
        """
        raise NotImplementedError()

    def add_interceptor(self, interceptor: Interceptor):
        if self.interceptor:
            self.interceptor = CombinedInterceptor(
                self.interceptor, interceptor)
        else:
            self.interceptor = interceptor

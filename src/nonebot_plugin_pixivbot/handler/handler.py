from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, TypeVar, Generic, Optional, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import Postman, PostIdentifier
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class Handler(ABC, Generic[UID, GID, B, M]):
    conf = context.require(Config)
    postman = context.require(Postman)

    interceptor: Optional[Interceptor] = None

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def enabled(cls) -> bool:
        raise NotImplementedError()

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> Union[dict, Awaitable[dict]]:
        """
        将位置参数转化为命名参数
        :param args: 位置参数sequence
        :param identifier: 发送者标识
        :return: 命名参数dict
        """
        return {}

    async def handle(self, *args,
                     post_dest: PostDestination[UID, GID, B, M],
                     silently: bool = False,
                     **kwargs):
        try:
            parsed_kwargs = self.parse_args(args, post_dest.identifier)
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
    async def actual_handle(self, post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False, **kwargs):
        """
        处理指令
        :param post_dest: PostDestination
        :param silently: 失败时不发送消息
        :param kwargs: 参数dict
        """
        raise NotImplementedError()

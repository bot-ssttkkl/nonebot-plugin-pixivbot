from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, TypeVar, Generic, Optional, Sequence, Any

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.postman import Postman
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")


class Handler(ABC, Generic[UID, GID]):
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
    async def actual_handle(self, post_dest: PostDestination[UID, GID],
                            silently: bool = False, **kwargs):
        """
        处理指令
        :param post_dest: PostDestination
        :param silently: 失败时不发送消息
        :param kwargs: 参数dict
        """
        raise NotImplementedError()

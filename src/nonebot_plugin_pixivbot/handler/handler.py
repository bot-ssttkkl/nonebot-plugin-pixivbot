from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, TypeVar, Sequence, Optional, Any

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .interceptor.combined_interceptor import CombinedInterceptor
from .interceptor.base import Interceptor
from .pkg_context import context
from ..context import Inject
from ..protocol_dep.postman import PostmanManager

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


@context.inject
class Handler(ABC):
    conf = Inject(Config)
    postman_manager = Inject(PostmanManager)

    def __init__(self):
        self.interceptor = None

    async def post_plain_text(self, message: str,
                              post_dest: PostDestination):
        await self.postman_manager.send_plain_text(message, post_dest=post_dest)

    async def post_illust(self, illust: Illust, *,
                          header: Optional[str] = None,
                          number: Optional[int] = None,
                          post_dest: PD):
        model = await IllustMessageModel.from_illust(illust, header=header, number=number)
        if model is not None:
            await self.postman_manager.send_illust(model, post_dest=post_dest)

    async def post_illusts(self, illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None,
                           post_dest: PD):
        model = await IllustMessagesModel.from_illusts(illusts, header=header, number=number)
        if model:
            await self.postman_manager.send_illusts(model, post_dest=post_dest)

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
            await self.interceptor.intercept(self._parse_args_and_actual_handle, *args,
                                             post_dest=post_dest,
                                             silently=silently,
                                             **kwargs)
        else:
            await self._parse_args_and_actual_handle(*args, post_dest=post_dest, silently=silently, **kwargs)

    async def handle_with_parsed_args(self, *, post_dest: PD,
                                      silently: bool = False,
                                      disabled_interceptors: bool = False,
                                      **kwargs):
        if not self.enabled():
            return

        if self.interceptor is not None and not disabled_interceptors:
            await self.interceptor.intercept(self.actual_handle,
                                             post_dest=post_dest,
                                             silently=silently,
                                             **kwargs)
        else:
            await self.actual_handle(post_dest=post_dest, silently=silently, **kwargs)

    async def _parse_args_and_actual_handle(self, *args,
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

from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, Sequence, Optional
from typing import Type

from nonebot.adapters import Bot, Event
from nonebot.internal.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Illust, T_UID, T_GID
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestinationFactoryManager, PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from .interceptor.base import Interceptor
from .interceptor.combined_interceptor import CombinedInterceptor
from .interceptor.data_source_session_interceptor import DataSourceSessionInterceptor
from .interceptor.default_error_interceptor import DefaultErrorInterceptor
from .interceptor.permission_interceptor import BlacklistInterceptor
from .pkg_context import context


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
                          post_dest: PostDestination[T_UID, T_GID]):
        model = await IllustMessageModel.from_illust(illust, header=header, number=number)
        if model is not None:
            await self.postman_manager.send_illust(model, post_dest=post_dest)

    async def post_illusts(self, illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None,
                           post_dest: PostDestination[T_UID, T_GID]):
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

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> Union[dict, Awaitable[dict]]:
        """
        将位置参数转化为命名参数
        :param args: 位置参数sequence
        :param post_dest: PostDestination
        :return: 命名参数dict
        """
        return {}

    async def handle(self, *args,
                     post_dest: PostDestination[T_UID, T_GID],
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

    async def handle_with_parsed_args(self, *, post_dest: PostDestination[T_UID, T_GID],
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
                                            post_dest: PostDestination[T_UID, T_GID],
                                            silently: bool = False,
                                            **kwargs):
        parsed_kwargs = self.parse_args(args, post_dest)
        if isawaitable(parsed_kwargs):
            parsed_kwargs = await parsed_kwargs

        kwargs = {**kwargs, **parsed_kwargs}
        await self.actual_handle(post_dest=post_dest, silently=silently, **kwargs)

    @abstractmethod
    async def actual_handle(self, *, post_dest: PostDestination[T_UID, T_GID],
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


def post_destination(bot: Bot, event: Event):
    return context.require(PostDestinationFactoryManager).from_event(bot, event)


class EntryHandler(Handler, ABC):
    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(DefaultErrorInterceptor))
        self.add_interceptor(context.require(BlacklistInterceptor))
        self.add_interceptor(context.require(DataSourceSessionInterceptor))


class MatcherEntryHandler(EntryHandler, ABC):
    def __init__(self):
        super().__init__()
        self.matcher.append_handler(self.on_match)

    @property
    @abstractmethod
    def matcher(self) -> Type[Matcher]:
        raise NotImplementedError()

    @abstractmethod
    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        raise NotImplementedError()


class DelegationHandler(Handler, ABC):
    @property
    @abstractmethod
    def delegation(self) -> Handler:
        raise NotImplementedError()

    async def handle(self, *args,
                     post_dest: PostDestination[T_UID, T_GID],
                     silently: bool = False,
                     disabled_interceptors: bool = False,
                     **kwargs):
        if not self.enabled():
            return

        await self.delegation.handle(*args, post_dest=post_dest, silently=silently,
                                     disabled_interceptors=disabled_interceptors, **kwargs)

    async def actual_handle(self, *args, **kwargs):
        raise RuntimeError("unexpected call here")

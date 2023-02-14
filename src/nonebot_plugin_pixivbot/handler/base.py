from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Awaitable, Union, Sequence, Optional
from typing import Type

from nonebot import logger
from nonebot.adapters import Bot, Event
from nonebot.internal.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Illust, T_UID, T_GID
from nonebot_plugin_pixivbot.model.message import IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestinationFactoryManager, PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from .interceptor.base import Interceptor
from .interceptor.combined_interceptor import CombinedInterceptor
from .interceptor.default_error_interceptor import DefaultErrorInterceptor
from .interceptor.permission_interceptor import BlacklistInterceptor
from .pkg_context import context
from ..plugin_service import r18_service, r18g_service


@context.inject
class Handler(ABC):
    conf: Config = Inject(Config)
    postman_manager: PostmanManager = Inject(PostmanManager)

    def __init__(self):
        self.interceptor = None

    async def post_plain_text(self, message: str,
                              post_dest: PostDestination):
        await self.postman_manager.send_plain_text(message, post_dest=post_dest)

    async def post_illust(self, illust: Illust, *,
                          header: Optional[str] = None,
                          number: Optional[int] = None,
                          post_dest: PostDestination[T_UID, T_GID]):
        block_r18 = not await r18_service.check_by_subject(*post_dest.extract_subjects(),
                                                           acquire_rate_limit_token=False)
        block_r18g = not await r18g_service.check_by_subject(*post_dest.extract_subjects(),
                                                             acquire_rate_limit_token=False)

        model = await IllustMessagesModel.from_illust(illust, header=header, number=number,
                                                      max_page=self.conf.pixiv_max_item_per_query,
                                                      block_r18=block_r18, block_r18g=block_r18g)
        if model:
            await self.postman_manager.send_illusts(model, post_dest=post_dest)

    async def post_illusts(self, illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None,
                           post_dest: PostDestination[T_UID, T_GID]):
        block_r18 = not await r18_service.check_by_subject(*post_dest.extract_subjects())
        block_r18g = not await r18g_service.check_by_subject(*post_dest.extract_subjects())

        if len(illusts) == 1:
            await self.post_illust(illusts[0], header=header, number=number, post_dest=post_dest)
        else:
            model = await IllustMessagesModel.from_illusts(illusts, header=header, number=number,
                                                           block_r18=block_r18, block_r18g=block_r18g)
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
                     disable_interceptors: bool = False,
                     **kwargs):
        if not self.enabled():
            return

        if self.interceptor is not None and not disable_interceptors:
            await self.interceptor.intercept(self._parse_args_and_actual_handle, *args,
                                             post_dest=post_dest,
                                             silently=silently,
                                             **kwargs)
        else:
            await self._parse_args_and_actual_handle(*args, post_dest=post_dest, silently=silently, **kwargs)

    async def handle_with_parsed_args(self, *, post_dest: PostDestination[T_UID, T_GID],
                                      silently: bool = False,
                                      disable_interceptors: bool = False,
                                      **kwargs):
        if not self.enabled():
            return

        if self.interceptor is not None and not disable_interceptors:
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

    def add_interceptor(self, interceptor: Interceptor, before: Optional[Type[Interceptor]] = None):
        """
        添加一个拦截器

        :param interceptor:
        :param before: 指定添加到哪个拦截器之前，若该拦截器不存在则默认添加到末尾
        :return:
        """
        if self.interceptor:
            if before is None:
                self.interceptor = CombinedInterceptor(self.interceptor, interceptor)
            elif isinstance(self.interceptor, CombinedInterceptor):
                itcps = list(self.interceptor.flat())
                for i, itcp in enumerate(itcps):
                    if isinstance(itcp, before):
                        self.interceptor = CombinedInterceptor.from_iterable([
                            *itcps[:i], interceptor, *itcps[i:]
                        ])
                        return

                self.interceptor = CombinedInterceptor(self.interceptor, interceptor)
                logger.warning("the interceptor specified by \'before\' argument was not found")
            elif isinstance(self.interceptor, before):
                self.interceptor = CombinedInterceptor(interceptor, self.interceptor)
            else:
                self.interceptor = CombinedInterceptor(self.interceptor, interceptor)
                logger.warning("the interceptor specified by \'before\' argument was not found")
        else:
            self.interceptor = interceptor
            if before is not None:
                logger.warning("the interceptor specified by \'before\' argument was not found")


def post_destination(bot: Bot, event: Event):
    return context.require(PostDestinationFactoryManager).from_event(bot, event)


class EntryHandler(Handler, ABC):
    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(DefaultErrorInterceptor))
        self.add_interceptor(context.require(BlacklistInterceptor))


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
    def __init__(self):
        super().__init__()
        if self.enabled():
            self.interceptor = self.delegation.interceptor

    @property
    @abstractmethod
    def delegation(self) -> Handler:
        raise NotImplementedError()

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> Union[dict, Awaitable[dict]]:
        return self.delegation.parse_args(args, post_dest)

    async def actual_handle(self, *, post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False,
                            **kwargs):
        return await self.delegation.actual_handle(post_dest=post_dest, silently=silently, **kwargs)

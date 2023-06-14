from abc import ABC, abstractmethod, ABCMeta
from asyncio import Event
from typing import Sequence, Optional
from typing import Type

from nonebot import logger
from nonebot_plugin_access_control.subject.extractor import extract_subjects_from_session
from nonebot_plugin_session import Session

from .interceptor.base import Interceptor, DummyInterceptor
from .interceptor.combined_interceptor import CombinedInterceptor
from .interceptor.default_error_interceptor import DefaultErrorInterceptor
from .interceptor.service_interceptor import ServiceInterceptor
from .pkg_context import context
from ..config import Config
from ..model import Illust
from ..model.message import IllustMessagesModel
from ..plugin_service import r18_service, r18g_service
from ..service.postman import Postman
from ..utils.algorithm import as_unique

conf = context.require(Config)


def _log_interceptors(cls: Type["Handler"]):
    if isinstance(cls.interceptor, CombinedInterceptor):
        logger.trace(
            f"{cls.__name__}: apply interceptors [{', '.join(map(lambda x: type(x).__name__, cls.interceptor.flat()))}]")
    else:
        logger.trace(f"{cls.__name__}: apply interceptors [{type(cls.interceptor).__name__}]")


class HandlerMeta(ABCMeta):
    interceptor: Interceptor

    def __new__(mcs, name, bases, namespace, **kwargs):
        interceptors = []

        if not kwargs.get("overwrite_interceptors", False):
            for base_cls in bases:
                if isinstance(base_cls, HandlerMeta):
                    if isinstance(base_cls.interceptor, CombinedInterceptor):
                        interceptors.extend(base_cls.interceptor.flat())
                    elif isinstance(base_cls.interceptor, DummyInterceptor):
                        pass
                    else:
                        interceptors.append(base_cls.interceptor)

        if "interceptors" in kwargs:
            interceptors.extend(kwargs["interceptors"])
            del kwargs["interceptors"]

        if "service" in kwargs:
            service = kwargs["service"]
            del kwargs["service"]

            if "service_interceptor_kwargs" in kwargs:
                service_interceptor_kwargs = kwargs["service_interceptor_kwargs"]
                del kwargs["service_interceptor_kwargs"]
            else:
                service_interceptor_kwargs = {}

            interceptors.insert(0, ServiceInterceptor(service, **service_interceptor_kwargs))

        interceptors = as_unique(interceptors)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if len(interceptors) == 0:
            cls.interceptor = DummyInterceptor()
        elif len(interceptors) == 1:
            cls.interceptor = interceptors[0]
        else:
            cls.interceptor = CombinedInterceptor.from_iterable(interceptors)

        _log_interceptors(cls)

        return cls


class Handler(ABC, metaclass=HandlerMeta):
    interceptor: Interceptor

    def __init__(self, session: Session, event: Optional[Event] = None,
                 *, silently: bool = False,
                 disable_interceptors: bool = False):
        self.session = session
        self.event = event
        self.silently = silently
        self.disable_interceptors = disable_interceptors

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def enabled(cls) -> bool:
        return True

    async def parse_args(self, args: Sequence[str]) -> dict:
        """
        将位置参数转化为命名参数
        :param args: 位置参数sequence
        :return: 命名参数dict
        """
        return {}

    async def handle(self, *args, **kwargs):
        if not self.disable_interceptors:
            await self.interceptor.intercept(self, self._parse_args_and_actual_handle, *args, **kwargs)
        else:
            await self._parse_args_and_actual_handle(*args, **kwargs)

    async def handle_with_parsed_args(self, **kwargs):
        if not self.disable_interceptors:
            await self.interceptor.intercept(self, self.actual_handle, **kwargs)
        else:
            await self.actual_handle(**kwargs)

    async def _parse_args_and_actual_handle(self, *args, **kwargs):
        parsed_kwargs = await self.parse_args(args)
        kwargs = {**kwargs, **parsed_kwargs}
        await self.actual_handle(**kwargs)

    @abstractmethod
    async def actual_handle(self, **kwargs):
        """
        处理指令
        :param kwargs: 参数dict
        """
        raise NotImplementedError()

    @classmethod
    def add_interceptor_before(cls, interceptor: Interceptor, before: Interceptor):
        """
        添加一个拦截器到指定拦截器之前

        :param interceptor:
        :param before: 指定添加到哪个拦截器之前
        """
        if isinstance(cls.interceptor, CombinedInterceptor):
            itcps = list(cls.interceptor.flat())
            for i, itcp in enumerate(itcps):
                if itcp is before:
                    cls.interceptor = CombinedInterceptor.from_iterable([
                        *itcps[:i], interceptor, *itcps[i:]
                    ])
                    break
            else:
                raise ValueError("the interceptor specified by \'before\' argument was not found")
        elif cls.interceptor is before:
            cls.interceptor = CombinedInterceptor(interceptor, cls.interceptor)
        else:
            raise ValueError("the interceptor specified by \'before\' argument was not found")

        _log_interceptors(cls)

    @classmethod
    def add_interceptor_after(cls, interceptor: Interceptor, after: Interceptor):
        """
        添加一个拦截器到指定拦截器之后

        :param interceptor:
        :param after: 指定添加到哪个拦截器之后
        """
        if isinstance(cls.interceptor, CombinedInterceptor):
            itcps = list(cls.interceptor.flat())
            for i, itcp in enumerate(itcps):
                if itcp is after:
                    cls.interceptor = CombinedInterceptor.from_iterable([
                        *itcps[:i + 1], interceptor, *itcps[i + 1:]
                    ])
                    break
            else:
                raise ValueError("the interceptor specified by \'after\' argument was not found")
        elif cls.interceptor is after:
            cls.interceptor = CombinedInterceptor(cls.interceptor, interceptor)
        else:
            raise ValueError("the interceptor specified by \'after\' argument was not found")

        _log_interceptors(cls)

    @classmethod
    def add_interceptor(cls, interceptor: Interceptor, front: bool = False):
        """
        添加一个拦截器

        :param interceptor:
        :param front: 添加到最前
        """
        if front:
            cls.interceptor = CombinedInterceptor(interceptor, cls.interceptor)
        else:
            cls.interceptor = CombinedInterceptor(cls.interceptor, interceptor)
        _log_interceptors(cls)

    async def is_r18_allowed(self) -> bool:
        return await r18_service.check_by_subject(*extract_subjects_from_session(self.session),
                                                  acquire_rate_limit_token=False)

    async def is_r18g_allowed(self) -> bool:
        return await r18g_service.check_by_subject(*extract_subjects_from_session(self.session),
                                                   acquire_rate_limit_token=False)

    async def post_plain_text(self, message: str):
        await context.require(Postman).post_plain_text(message, self.session, self.event)

    async def post_illust(self, illust: Illust, *,
                          header: Optional[str] = None,
                          number: Optional[int] = None):
        model = await IllustMessagesModel.from_illust(illust, header=header, number=number,
                                                      max_page=conf.pixiv_max_item_per_query,
                                                      block_r18=(not await self.is_r18_allowed()),
                                                      block_r18g=(not await self.is_r18g_allowed()))
        if model:
            await context.require(Postman).post_illusts(model, self.session, self.event)

    async def post_illusts(self, illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None):
        if len(illusts) == 1:
            await self.post_illust(illusts[0], header=header, number=number)
        else:
            model = await IllustMessagesModel.from_illusts(illusts, header=header, number=number,
                                                           block_r18=(not await self.is_r18_allowed()),
                                                           block_r18g=(not await self.is_r18g_allowed()))
            if model:
                await context.require(Postman).post_illusts(model, self.session, self.event)


class EntryHandler(Handler, ABC, interceptors=[context.require(DefaultErrorInterceptor)]):
    pass

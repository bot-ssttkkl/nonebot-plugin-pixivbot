from abc import ABC, abstractmethod
from asyncio import Lock
from contextlib import AbstractContextManager
from inspect import isawaitable
from types import TracebackType
from typing import Any, Awaitable, Generic, TypeVar, Callable, Union, AsyncGenerator, List, Type, Optional

from nonebot import logger

T_ITEM = TypeVar("T_ITEM")


class SharedAsyncGeneratorContextManager(AbstractContextManager, Generic[T_ITEM]):
    def __init__(self, origin: AsyncGenerator[T_ITEM, None],
                 on_stop: Callable[[List[T_ITEM]],
                                   Union[None, Awaitable[None]]],
                 on_consumers_changed: Callable[["SharedAsyncGeneratorContextManager", int], None]):
        super().__init__()
        self._origin = origin
        self._stopped = False  # whether origin has raised a StopIteration
        self._got_items = []  # items got from origin, used to replay
        self._got = 0  # count of items got from origin
        self._mutex = Lock()  # for coroutine safety
        self._consumers = 0  # count of consumer
        self._on_stop = on_stop  # callback on origin stops iteration
        self._on_consumers_changed = on_consumers_changed  # callback on a consumer enters or exits

    @property
    def consumers(self) -> int:
        return self._consumers

    async def _generator_factory(self) -> AsyncGenerator[T_ITEM, None]:
        cur = 0
        while True:
            if cur < self._got:
                yield self._got_items[cur]
                cur += 1
            else:
                if self._stopped:
                    break

                async with self._mutex:
                    try:
                        if cur == self._got:
                            new_data = await self._origin.__anext__()
                            self._got_items.append(new_data)
                            self._got += 1
                        yield self._got_items[cur]
                        cur += 1
                    except StopAsyncIteration:
                        self._stopped = True
                        x = self._on_stop(self._got_items)
                        if isawaitable(x):
                            await x

    def __enter__(self) -> AsyncGenerator[T_ITEM, None]:
        self._consumers += 1
        self._on_consumers_changed(self, self._consumers)
        return self._generator_factory()

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self._consumers -= 1
        self._on_consumers_changed(self, self._consumers)

    def close(self):
        self._origin.athrow(GeneratorExit)


T_ID = TypeVar("T_ID")


class AbstractMediator(ABC, Generic[T_ID]):
    def __init__(self):
        self._ctx_mgr = {}
        self._stopped_ctx_mgr = {}  # TODO: Cache Control, with exact expires time

    @abstractmethod
    def agen_factory(self, identifier: T_ID, *args, **kwargs) -> AsyncGenerator[T_ITEM, None]:
        raise NotImplementedError()

    @abstractmethod
    def on_agen_stop(self, identifier: T_ID, items: List[T_ITEM]) -> Union[None, Awaitable[None]]:
        raise NotImplementedError()

    def on_consumers_changed(self, identifier: T_ID,
                             ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM],
                             consumers: int):
        if identifier in self._stopped_ctx_mgr and consumers > 0:
            logger.debug(f"[mediator] {identifier} re-started")
            del self._stopped_ctx_mgr[identifier]
            self._ctx_mgr[identifier] = ctx_mgr
        elif identifier in self._ctx_mgr and consumers == 0:
            logger.debug(f"[mediator] {identifier} stopped")
            del self._ctx_mgr[identifier]
            self._stopped_ctx_mgr[identifier] = ctx_mgr

    def get(self, identifier: Any, *args, **kwargs) -> SharedAsyncGeneratorContextManager[T_ITEM]:
        if identifier in self._stopped_ctx_mgr:
            return self._stopped_ctx_mgr[identifier]
        elif identifier in self._ctx_mgr:
            return self._ctx_mgr[identifier]
        else:
            self._ctx_mgr[identifier] = SharedAsyncGeneratorContextManager(
                origin=self.agen_factory(identifier, *args, **kwargs),
                on_stop=lambda items: self.on_agen_stop(identifier, items),
                on_consumers_changed=lambda ctx_mgr, consumers: self.on_consumers_changed(
                    identifier, ctx_mgr, consumers)
            )
            return self._ctx_mgr[identifier]

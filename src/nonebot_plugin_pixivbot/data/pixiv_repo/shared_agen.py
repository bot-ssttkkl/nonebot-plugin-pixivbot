from abc import ABC, abstractmethod
from asyncio import Lock, create_task
from contextlib import AbstractContextManager
from datetime import datetime
from inspect import isawaitable
from types import TracebackType
from typing import Any, Awaitable, Generic, TypeVar, Callable, Union, AsyncGenerator, List, Type, Optional, Dict

from nonebot import logger

from nonebot_plugin_pixivbot.utils.expires_lru_dict import ExpiresLruDict

T_ID = TypeVar("T_ID")
T_ITEM = TypeVar("T_ITEM")


class SharedAsyncGeneratorContextManager(AbstractContextManager, Generic[T_ITEM]):
    def __init__(self, origin: AsyncGenerator[T_ITEM, None],
                 on_each: Callable[[T_ITEM], Union[None, Awaitable[None]]],
                 on_stop: Callable[[List[T_ITEM]],
                                   Union[None, Awaitable[None]]],
                 on_consumers_changed: Callable[["SharedAsyncGeneratorContextManager", int], None]):
        super().__init__()
        self._origin = origin
        self._stopped = False  # whether origin has raised a StopIteration
        self._got_items = []  # items got from origin, used to replay
        self._got = 0  # count of items got from origin
        self._mutex = Lock()  # to solve race
        self._consumers = 0  # count of consumer
        self._on_each = on_each  # callback on origin yields
        self._on_stop = on_stop  # callback on origin stops
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
                    if self._stopped:
                        break

                    try:
                        if cur == self._got:
                            new_data = await self._origin.__anext__()
                            await self._on_each(new_data)
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

    async def aclose(self):
        return await self._origin.aclose()

    def close(self):
        create_task(self.aclose())


class SharedAsyncGeneratorManager(ABC, Generic[T_ID, T_ITEM]):
    def __init__(self):
        self._ctx_mgr = {}
        self._paused_ctx_mgr = ExpiresLruDict(1024, SharedAsyncGeneratorManager._cleanup)
        self._expires_time: Dict[T_ID, datetime] = {}

    @abstractmethod
    def agen_factory(self, identifier: T_ID, *args, **kwargs) -> AsyncGenerator[T_ITEM, None]:
        raise NotImplementedError()

    def on_agen_next(self, identifier: T_ID, item: T_ITEM) -> Union[None, Awaitable[None]]:
        pass

    def on_agen_stop(self, identifier: T_ID, items: List[T_ITEM]) -> Union[None, Awaitable[None]]:
        pass

    @staticmethod
    def _cleanup(identifier: T_ID, ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM]):
        ctx_mgr.close()

    def on_consumers_changed(self, identifier: T_ID,
                             ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM],
                             consumers: int):
        if identifier in self._paused_ctx_mgr and consumers > 0:
            logger.debug(f"[agen_manager] {identifier} re-started")
            del self._paused_ctx_mgr[identifier]
            self._ctx_mgr[identifier] = ctx_mgr
        elif identifier in self._ctx_mgr and consumers == 0:
            del self._ctx_mgr[identifier]
            self._cleanup(identifier, ctx_mgr)
            if identifier in self._expires_time:
                logger.debug(f"[agen_manager] {identifier} paused")
                self._paused_ctx_mgr.add(identifier, ctx_mgr, self._expires_time[identifier])
            else:
                logger.debug(f"[agen_manager] {identifier} stopped")

    def get_expires_time(self, identifier: T_ID) -> Optional[datetime]:
        return self._expires_time.get(identifier, None)

    def set_expires_time(self, identifier: T_ID, expires_time: datetime):
        if identifier not in self._expires_time:
            self._expires_time[identifier] = expires_time
            logger.debug(f"[agen_manager] {identifier} will expire at {expires_time}")
        elif self._expires_time[identifier] != expires_time:
            raise RuntimeError(f"{identifier} expires time already set")

    def get(self, identifier: Any, *args, **kwargs) \
            -> SharedAsyncGeneratorContextManager[T_ITEM]:
        if identifier in self._paused_ctx_mgr:
            return self._paused_ctx_mgr[identifier]
        elif identifier in self._ctx_mgr:
            return self._ctx_mgr[identifier]
        else:
            origin = self.agen_factory(identifier, *args, **kwargs)
            self._ctx_mgr[identifier] = SharedAsyncGeneratorContextManager(
                origin=origin,
                on_each=lambda item: self.on_agen_next(identifier, item),
                on_stop=lambda items: self.on_agen_stop(identifier, items),
                on_consumers_changed=lambda ctx_mgr, consumers: self.on_consumers_changed(
                    identifier, ctx_mgr, consumers)
            )
            return self._ctx_mgr[identifier]
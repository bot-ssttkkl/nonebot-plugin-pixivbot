import time
from abc import ABC, abstractmethod
from asyncio import Lock
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import Any, Generic, TypeVar, AsyncGenerator, List, Type, Optional, AsyncContextManager

from cachetools import TLRUCache
from nonebot import logger

from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy

T_ID = TypeVar("T_ID")
T_ITEM = TypeVar("T_ITEM")


class SharedAsyncGeneratorManager(ABC, Generic[T_ID, T_ITEM]):
    log_tag = "shared_agen"

    class _AgenHolder(AbstractAsyncContextManager):
        def __init__(self, origin: AsyncGenerator[T_ITEM, None],
                     identifier: T_ID,
                     manager: "SharedAsyncGeneratorManager"):
            super().__init__()
            self._origin = origin
            self._stopped = False  # whether origin has raised a StopIteration
            self._got_items = []  # items got from origin, used to replay
            self._got = 0  # count of items got from origin
            self._mutex = Lock()  # to solve race
            self._consumers = 0  # count of consumer

            self._identifier = identifier
            self._manager = manager

        @property
        def consumers(self) -> int:
            return self._consumers

        async def _generator(self) -> AsyncGenerator[T_ITEM, None]:
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

                        if cur == self._got:
                            try:
                                new_data = await self._origin.__anext__()
                            except StopAsyncIteration:
                                self._stopped = True
                                await self._manager.on_agen_stop(self._identifier, self._got_items)
                                break
                            except Exception as e:
                                logger.error(f"error {type(e)} raised by agen {self._identifier}")
                                await self._manager.on_agen_error(self._identifier, e)
                                raise e

                            await self._manager.on_agen_next(self._identifier, new_data)

                            self._got_items.append(new_data)
                            self._got += 1

                        yield self._got_items[cur]
                        cur += 1

        async def __aenter__(self) -> AsyncGenerator[T_ITEM, None]:
            self._consumers += 1
            await self._manager._on_consumers_changed(self._identifier, self, self._consumers)
            return self._generator()

        async def __aexit__(self, exc_type: Optional[Type[BaseException]],
                            exc_value: Optional[BaseException],
                            traceback: Optional[TracebackType]) -> None:
            self._consumers -= 1
            await self._manager._on_consumers_changed(self._identifier, self, self._consumers)

        async def aclose(self):
            return await self._origin.aclose()

    def __init__(self):
        self._running_holders = dict[T_ID, self._AgenHolder]()
        self._expires_time = dict[T_ID, float]()

        self._stopped_holders = TLRUCache[T_ID, self._AgenHolder](maxsize=2048,
                                                                  ttu=lambda k, v, now: self._expires_time[k],
                                                                  timer=time.time)

    @abstractmethod
    def agen(self, identifier: T_ID,
             cache_strategy: CacheStrategy,
             **kwargs) -> AsyncGenerator[T_ITEM, None]:
        raise NotImplementedError()

    async def on_agen_next(self, identifier: T_ID, item: T_ITEM):
        pass

    async def on_agen_stop(self, identifier: T_ID, items: List[T_ITEM]):
        # 如果用户手动调用invalidate，该holder已不存在于self._running_holders中
        # 自然也不需要缓存到self._stopped_holders中
        if identifier in self._running_holders:
            holder = self._running_holders.pop(identifier)
            self._stopped_holders[identifier] = holder
            logger.debug(f"[{self.log_tag}] {identifier} was stopped and cached")

    async def on_agen_error(self, identifier: T_ID, e: Exception):
        await self.invalidate(identifier)

    async def _on_consumers_changed(self, identifier: T_ID,
                                    holder: _AgenHolder,
                                    consumers: int):
        if identifier in self._running_holders and consumers == 0:
            del self._running_holders[identifier]

            if identifier in self._expires_time:
                del self._expires_time[identifier]

            await holder.aclose()
            logger.debug(f"[{self.log_tag}] {identifier} cannot be reused "
                         "(the origin agen hasn't stopped when all consumers exited)")

    async def invalidate(self, identifier: T_ID):
        if identifier in self._stopped_holders:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from cached state")
            del self._stopped_holders[identifier]
        elif identifier in self._running_holders:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from running state")
            holder = self._running_holders.pop(identifier)
            await holder.aclose()

            if identifier in self._expires_time:
                del self._expires_time[identifier]
        else:
            logger.warning(f"[{self.log_tag}] {identifier} was not found")
            return

    async def invalidate_all(self):
        keys = {*self._stopped_holders.keys(), *self._running_holders.keys()}
        for k in keys:
            await self.invalidate(k)

    def get_expires_time(self, identifier: T_ID) -> Optional[float]:
        if identifier in self._stopped_holders:
            t = self._stopped_holders.__getitem(identifier).expires
            return t
        elif identifier in self._running_holders:
            t = self._expires_time.get(identifier, None)
            return t
        else:
            return None

    async def set_expires_time(self, identifier: T_ID, expires_time: float):
        now = time.time()
        if expires_time <= now:
            await self.invalidate(identifier)
            logger.debug(f"[{self.log_tag}] {identifier} was expired "
                         "(due to a past expires time was set)")
            return

        if identifier in self._stopped_holders:
            holder = self._stopped_holders.pop(identifier)

            if expires_time > now:
                self._expires_time[identifier] = expires_time
                self._stopped_holders[identifier] = holder
                del self._expires_time[identifier]

                logger.debug(f"[{self.log_tag}] {identifier} will expires at {expires_time}")
        elif identifier in self._running_holders:
            self._expires_time[identifier] = expires_time
            logger.debug(f"[{self.log_tag}] {identifier} will expire at {expires_time}")
        else:
            logger.warning(f"[{self.log_tag}] {identifier} was not found")

    @asynccontextmanager
    async def get(self, identifier: Any,
                  cache_strategy: CacheStrategy = CacheStrategy.NORMAL,
                  **kwargs) -> AsyncContextManager[AsyncGenerator[T_ITEM, None]]:
        if cache_strategy == CacheStrategy.FORCE_EXPIRATION:
            await self.invalidate(identifier)

        holder = self._stopped_holders.get(identifier, None)
        if holder is None:
            holder = self._running_holders.get(identifier, None)
            if holder is None:
                origin = self.agen(identifier, cache_strategy, **kwargs)
                holder = self._AgenHolder(origin, identifier, self)
                logger.debug(f"[{self.log_tag}] {identifier} was created")
                self._running_holders[identifier] = holder

        async with holder as x:
            yield x


__all__ = ("SharedAsyncGeneratorManager",)

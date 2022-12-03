from abc import ABC, abstractmethod
from asyncio import Lock
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime, timezone
from types import TracebackType
from typing import Any, Generic, TypeVar, AsyncGenerator, List, Type, Optional, Dict, \
    AsyncContextManager

from nonebot import logger

from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.utils.expires_lru_dict import AsyncExpiresLruDict

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
        self._working_holders = dict[T_ID, self._AgenHolder]()
        self._paused_holders = AsyncExpiresLruDict[T_ID, self._AgenHolder](1024, self._cleanup)
        self._expires_time = dict[T_ID, datetime]()

    @abstractmethod
    def agen(self, identifier: T_ID,
             cache_strategy: CacheStrategy,
             **kwargs) -> AsyncGenerator[T_ITEM, None]:
        raise NotImplementedError()

    async def on_agen_next(self, identifier: T_ID, item: T_ITEM):
        pass

    async def on_agen_stop(self, identifier: T_ID, items: List[T_ITEM]):
        pass

    async def on_agen_error(self, identifier: T_ID, e: Exception):
        await self.invalidate(identifier)

    async def _cleanup(self, identifier: T_ID, holder: _AgenHolder):
        logger.debug(f"[{self.log_tag}] {identifier} was popped")
        await holder.aclose()
        if identifier in self._expires_time:
            del self._expires_time[identifier]

    async def _on_consumers_changed(self, identifier: T_ID,
                                    holder: _AgenHolder,
                                    consumers: int):
        if await self._paused_holders.contains(identifier) and consumers > 0:
            logger.debug(f"[{self.log_tag}] {identifier} re-started")
            await self._paused_holders.pop(identifier)
            self._working_holders[identifier] = holder
        elif identifier in self._working_holders and consumers == 0:
            del self._working_holders[identifier]
            if identifier in self._expires_time:
                logger.debug(f"[{self.log_tag}] {identifier} paused")
                await self._paused_holders.add(identifier, holder, self._expires_time[identifier])
            else:
                await self._cleanup(identifier, holder)
                logger.debug(f"[{self.log_tag}] {identifier} stopped")

    async def invalidate(self, identifier: T_ID):
        if await self._paused_holders.contains(identifier):
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from paused state")
            holder = await self._paused_holders.pop(identifier)
            await holder.aclose()
        elif identifier in self._working_holders:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from running state")
            self._working_holders.pop(identifier)

        if identifier in self._expires_time:
            del self._expires_time[identifier]

    async def invalidate_all(self):
        keys = list(x async for x in self._paused_holders.iter())
        for identifier in keys:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from paused state")
            holder = await self._paused_holders.pop(identifier)
            await holder.aclose()

        keys = list(self._working_holders.keys())
        for identifier in keys:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from running state")
            self._working_holders.pop(identifier)

        self._expires_time.clear()

    def get_expires_time(self, identifier: T_ID) -> Optional[datetime]:
        return self._expires_time.get(identifier, None)

    async def set_expires_time(self, identifier: T_ID, expires_time: datetime):
        # 即使当前没有该holder也可以设置
        # 在调用invalidate或者被_paused_holder弹出后从_expires_time中删除
        if expires_time <= datetime.now(timezone.utc):
            await self.invalidate(identifier)
        elif identifier not in self._expires_time:
            self._expires_time[identifier] = expires_time
            logger.debug(f"[{self.log_tag}] {identifier} will expire at {expires_time}")
        elif self._expires_time[identifier] != expires_time:
            logger.warning(f"[{self.log_tag}] {identifier}'s expires time was already set")

    @asynccontextmanager
    async def get(self, identifier: Any,
                  cache_strategy: CacheStrategy = CacheStrategy.NORMAL,
                  **kwargs) -> AsyncContextManager[AsyncGenerator[T_ITEM, None]]:
        if cache_strategy == CacheStrategy.FORCE_EXPIRATION:
            await self.invalidate(identifier)

        holder = await self._paused_holders.get(identifier)
        if holder is None:
            holder = self._working_holders.get(identifier, None)
            if holder is None:
                origin = self.agen(identifier, cache_strategy, **kwargs)
                holder = self._AgenHolder(origin, identifier, self)
                self._working_holders[identifier] = holder

        async with holder as x:
            yield x


__all__ = ("SharedAsyncGeneratorManager",)

from abc import ABC, abstractmethod
from asyncio import Lock, create_task
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from inspect import isawaitable
from types import TracebackType
from typing import Any, Awaitable, Generic, TypeVar, Callable, Union, AsyncGenerator, List, Type, Optional, Dict

from nonebot import logger

from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.utils.expires_lru_dict import ExpiresLruDict

T_ID = TypeVar("T_ID")
T_ITEM = TypeVar("T_ITEM")


class SharedAsyncGeneratorContextManager(AbstractContextManager, Generic[T_ITEM]):
    def __init__(self, origin: AsyncGenerator[T_ITEM, None],
                 *, on_each: Optional[Callable[[T_ITEM], Union[None, Awaitable[None]]]] = None,
                 on_error: Optional[Callable[[Exception], Union[None, Awaitable[None]]]] = None,
                 on_stop: Optional[Callable[[List[T_ITEM]], Union[None, Awaitable[None]]]] = None,
                 on_consumers_changed: Optional[Callable[["SharedAsyncGeneratorContextManager", int], None]] = None):
        super().__init__()
        self._origin = origin
        self._stopped = False  # whether origin has raised a StopIteration
        self._got_items = []  # items got from origin, used to replay
        self._got = 0  # count of items got from origin
        self._mutex = Lock()  # to solve race
        self._consumers = 0  # count of consumer
        self._on_each = on_each  # callback on origin yields
        self._on_error = on_error  # callback on origin throws
        self._on_stop = on_stop  # callback on origin stops
        self._on_consumers_changed = on_consumers_changed  # callback on a consumer enters or exits

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

                            if self._on_stop:
                                ret = self._on_stop(self._got_items)
                                if isawaitable(ret):
                                    await ret

                            break
                        except Exception as e:
                            if self._on_error:
                                ret = self._on_error(e)
                                if isawaitable(ret):
                                    await ret
                            raise e

                        if self._on_each:
                            ret = self._on_each(new_data)
                            if isawaitable(ret):
                                await ret

                        self._got_items.append(new_data)
                        self._got += 1

                    yield self._got_items[cur]
                    cur += 1

    def __enter__(self) -> AsyncGenerator[T_ITEM, None]:
        self._consumers += 1

        if self._on_consumers_changed:
            self._on_consumers_changed(self, self._consumers)

        return self._generator()

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self._consumers -= 1

        if self._on_consumers_changed:
            self._on_consumers_changed(self, self._consumers)

    async def aclose(self):
        return await self._origin.aclose()

    def close(self):
        create_task(self.aclose())


class SharedAsyncGeneratorManager(ABC, Generic[T_ID, T_ITEM]):
    log_tag = "shared_agen"

    def __init__(self):
        self._ctx_mgr = {}
        self._paused_ctx_mgr = ExpiresLruDict(1024, self._cleanup)
        self._expires_time: Dict[T_ID, datetime] = {}

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
        self.invalidate(identifier)

    def _cleanup(self, identifier: T_ID, ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM]):
        logger.debug(f"[{self.log_tag}] {identifier} was popped")
        ctx_mgr.close()
        if identifier in self._expires_time:
            del self._expires_time[identifier]

    def on_consumers_changed(self, identifier: T_ID,
                             ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM],
                             consumers: int):
        if identifier in self._paused_ctx_mgr and consumers > 0:
            logger.debug(f"[{self.log_tag}] {identifier} re-started")
            del self._paused_ctx_mgr[identifier]
            self._ctx_mgr[identifier] = ctx_mgr
        elif identifier in self._ctx_mgr and consumers == 0:
            del self._ctx_mgr[identifier]
            if identifier in self._expires_time:
                logger.debug(f"[{self.log_tag}] {identifier} paused")
                self._paused_ctx_mgr.add(identifier, ctx_mgr, self._expires_time[identifier])
            else:
                self._cleanup(identifier, ctx_mgr)
                logger.debug(f"[{self.log_tag}] {identifier} stopped")

    def invalidate(self, identifier: T_ID):
        if identifier in self._paused_ctx_mgr:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from paused state")
            self._paused_ctx_mgr.pop(identifier).close()
        elif identifier in self._ctx_mgr:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from running state")
            self._ctx_mgr.pop(identifier)

        if identifier in self._expires_time:
            del self._expires_time[identifier]

    def invalidate_all(self):
        keys = list(self._paused_ctx_mgr.keys())
        for identifier in keys:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from paused state")
            self._paused_ctx_mgr.pop(identifier).close()

        keys = list(self._ctx_mgr.keys())
        for identifier in keys:
            logger.debug(f"[{self.log_tag}] {identifier} was invalidated from running state")
            self._ctx_mgr.pop(identifier)

        self._expires_time.clear()

    def get_expires_time(self, identifier: T_ID) -> Optional[datetime]:
        return self._expires_time.get(identifier, None)

    def set_expires_time(self, identifier: T_ID, expires_time: datetime):
        # 即使当前没有该ctx_mgr也可以设置
        # 在调用invalidate或者被_paused_ctx_mgr弹出后从_expires_time中删除
        if expires_time <= datetime.now(timezone.utc):
            self.invalidate(identifier)
        elif identifier not in self._expires_time:
            self._expires_time[identifier] = expires_time
            logger.debug(f"[{self.log_tag}] {identifier} will expire at {expires_time}")
        elif self._expires_time[identifier] != expires_time:
            logger.warning(f"[{self.log_tag}] {identifier}'s expires time was already set")

    def get(self, identifier: Any,
            cache_strategy: CacheStrategy = CacheStrategy.NORMAL,
            **kwargs) \
            -> SharedAsyncGeneratorContextManager[T_ITEM]:
        if cache_strategy == CacheStrategy.FORCE_EXPIRATION:
            self.invalidate(identifier)

        if identifier in self._paused_ctx_mgr:
            return self._paused_ctx_mgr[identifier]
        elif identifier in self._ctx_mgr:
            return self._ctx_mgr[identifier]
        else:
            origin = self.agen(identifier, cache_strategy, **kwargs)
            self._ctx_mgr[identifier] = SharedAsyncGeneratorContextManager(
                origin=origin,
                on_each=lambda item: self.on_agen_next(identifier, item),
                on_stop=lambda items: self.on_agen_stop(identifier, items),
                on_error=lambda e: self.on_agen_error(identifier, e),
                on_consumers_changed=lambda ctx_mgr, consumers: self.on_consumers_changed(
                    identifier, ctx_mgr, consumers)
            )
            return self._ctx_mgr[identifier]

import asyncio
import typing


class CacheManager:
    def __init__(self, simultaneous_query: int = 4):
        self._semaphore = asyncio.Semaphore(
            value=simultaneous_query)  # 用于限制从远程获取的并发量
        self._waiting = {}

    T = typing.TypeVar("T")

    async def get(self, identifier: typing.Any,
                  cache_loader: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  cache_updater: typing.Callable[[T], typing.Coroutine[typing.Any, typing.Any, typing.NoReturn]],
                  timeout: typing.Optional[int] = 0) -> T:
        cache = await cache_loader()
        if cache is not None:
            return cache

        if identifier in self._waiting:
            return await self._waiting[identifier]

        fut = asyncio.Future()
        self._waiting[identifier] = fut
        try:
            asyncio.create_task(self._fetch(
                fut, remote_fetcher, cache_updater, timeout))
            return await fut
        finally:
            await self._waiting.pop(identifier)

    async def _fetch(self, fut: asyncio.Future,
                     remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                     cache_updater: typing.Callable[[T], typing.Coroutine[typing.Any, typing.Any, typing.NoReturn]],
                     timeout: typing.Optional[float] = None):
        await self._semaphore.acquire()
        try:
            result = await asyncio.wait_for(remote_fetcher(), timeout)
            await cache_updater(result)
            fut.set_result(result)
        except Exception as e:
            fut.set_exception(e)
        finally:
            self._semaphore.release()


__all__ = ("CacheManager",)

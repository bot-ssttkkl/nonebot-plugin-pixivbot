import asyncio
import sys
import typing


class CacheManager:
    _semaphore: asyncio.Semaphore
    _waiting: typing.Dict[typing.Any, asyncio.Future]

    def __init__(self, simultaneous_query: int = 4,
                 loop: typing.Optional[asyncio.AbstractEventLoop] = None):
        if sys.version_info >= (3, 10, 0):
            self._semaphore = asyncio.Semaphore(value=simultaneous_query)  # 限制从远程获取的并发量为8
        else:
            self._semaphore = asyncio.Semaphore(value=simultaneous_query, loop=loop)
        self._waiting = {}

    T = typing.TypeVar("T")

    async def get(self, identifier: typing.Any,
                  cache_loader: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  cache_updater: typing.Callable[[], typing.Coroutine],
                  timeout: typing.Optional[int] = 0) -> T:
        cache = await cache_loader()
        if cache is not None:
            return cache

        if identifier in self._waiting:
            return await self._waiting[identifier]

        fut = asyncio.Future()
        self._waiting[identifier] = fut
        asyncio.create_task(self._fetch(
            fut, remote_fetcher, cache_updater, timeout))
        result = await fut

        await self._waiting.pop(identifier)

        return result

    async def _fetch(self, fut: asyncio.Future,
                     remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                     cache_updater: typing.Callable[[T], typing.Coroutine],
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

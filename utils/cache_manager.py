import asyncio
import typing

from nonebot import logger


class CacheManager:
    _query_queue: asyncio.Queue
    _done_queue: asyncio.Queue
    _waiting: typing.Dict[typing.Any, asyncio.Event]
    _worker_task: asyncio.Task = None

    def __init__(self):
        self._query_queue = asyncio.Queue()
        self._done_queue = asyncio.Queue()
        self._waiting = {}
        self._worker_task = None

    def start(self) -> bool:
        self._worker_task = asyncio.create_task(self._worker())
        return True

    def stop(self) -> bool:
        t = self._worker_task
        if t is None or t.cancelled():
            return False
        return t.cancel()

    T = typing.TypeVar("T")

    async def get(self, identifier: typing.Any,
                  cache_loader: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                  cache_updater: typing.Callable[[], typing.Coroutine],
                  timeout: typing.Optional[int] = 0) -> T:
        cache = await cache_loader()
        if cache is not None:
            return cache

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        await self._query_queue.put(("get", fut, identifier, cache_loader, remote_fetcher, cache_updater, timeout))
        return await fut

    async def _worker(self):
        pending = [
            asyncio.create_task(self._query_queue.get()),
            asyncio.create_task(self._done_queue.get()),
        ]
        while True:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for c in done:
                try:
                    res = await c
                    if res[0] == "get":
                        try:
                            await self._on_get(*res[1:])
                        finally:
                            self._query_queue.task_done()
                            pending.add(asyncio.create_task(self._query_queue.get()))
                    elif res[0] == "done":
                        try:
                            self._on_done(*res[1:])
                        finally:
                            self._done_queue.task_done()
                            pending.add(asyncio.create_task(self._done_queue.get()))
                except Exception as e:
                    logger.exception(e)

    async def _on_get(self, fut: asyncio.Future,
                      identifier: typing.Any,
                      cache_loader: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                      remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                      cache_updater: typing.Callable[[], typing.Coroutine],
                      timeout: typing.Optional[int] = 0):
        cache = await cache_loader()
        if cache is not None:
            fut.set_result(cache)
        elif identifier in self._waiting:
            event = self._waiting[identifier]
            asyncio.create_task(self._wait_and_load_cache(event, fut, cache_loader))
        else:
            event = asyncio.Event()
            self._waiting[identifier] = event
            asyncio.create_task(self._get_and_cache(fut, identifier, event, remote_fetcher, cache_updater, timeout))

    def _on_done(self, identifier: typing.Any):
        self._waiting.pop(identifier)

    async def _get_and_cache(self, fut: asyncio.Future,
                             identifier: typing.Any,
                             event: asyncio.Event,
                             remote_fetcher: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
                             cache_updater: typing.Callable[[T], typing.Coroutine],
                             timeout: typing.Optional[int] = 0):
        try:
            result = await asyncio.wait_for(remote_fetcher(), timeout)
            fut.set_result(result)

            await cache_updater(result)
        except Exception as e:
            fut.set_exception(e)
        finally:
            await self._done_queue.put(("done", identifier))
            event.set()

    @staticmethod
    async def _wait_and_load_cache(event: asyncio.Event,
                                   fut: asyncio.Future,
                                   cache_loader: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]]):
        try:
            await event.wait()
            cache = await cache_loader()
            fut.set_result(cache)
        except Exception as e:
            fut.set_exception(e)


__all__ = ("CacheManager",)

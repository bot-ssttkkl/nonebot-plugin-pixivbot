from asyncio import Future, Semaphore, wait_for, create_task
from inspect import isawaitable
from typing import TypeVar, NoReturn, Optional, Any, Callable, Union, Awaitable, AsyncGenerator, List, Coroutine

from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import NoSuchItemError


class Mediator:
    def __init__(self, simultaneous_query: int):
        self._semaphore = Semaphore(value=simultaneous_query)  # 用于限制从远程获取的并发量
        self._waiting = {}

    T = TypeVar("T")

    async def mixin(self, identifier: Any,
                    cache_loader: Callable[[], Union[T, Awaitable[T]]],
                    remote_fetcher: Callable[[], Union[T, Awaitable[T]]],
                    cache_updater: Callable[[T], Coroutine[None, None, NoReturn]],
                    hook_on_cache: Optional[Callable[[T], T]] = None,
                    hook_on_fetch: Optional[Callable[[T], T]] = None) -> T:
        try:
            cache = cache_loader()
            if isawaitable(cache):
                cache = await cache
            if cache is None:
                raise NoSuchItemError()
        except NoSuchItemError:
            if identifier in self._waiting:
                return await self._waiting[identifier]

            fut = Future()
            self._waiting[identifier] = fut
            try:
                create_task(self._fetch(fut, remote_fetcher, cache_updater))
                result = await fut
                if hook_on_fetch:
                    result = hook_on_fetch(result)
                return result
            finally:
                await self._waiting.pop(identifier)

        if hook_on_cache:
            cache = hook_on_cache(cache)
        return cache

    async def mixin_async_generator(self, identifier: Any,
                                    cache_loader: Callable[[], AsyncGenerator[T, None]],
                                    remote_fetcher: Callable[[], AsyncGenerator[T, None]],
                                    cache_updater: Callable[[List[T]], Coroutine[None, None, NoReturn]],
                                    hook_on_cache: Optional[Callable[[T], T]] = None,
                                    hook_on_fetch: Optional[Callable[[T], T]] = None) -> AsyncGenerator[T, None]:
        try:
            if hook_on_cache:
                async for x in cache_loader():
                    yield hook_on_cache(x)
            else:
                async for x in cache_loader():
                    yield x
        except NoSuchItemError:
            if identifier not in self._waiting:
                fut = Future()
                self._waiting[identifier] = fut

                try:
                    result = []
                    async for x in remote_fetcher():
                        result.append(x)
                        if hook_on_fetch:
                            x = hook_on_fetch(x)
                        yield x
                    await cache_updater(result)
                    fut.set_result(result)
                except Exception as e:
                    fut.set_exception(e)
                finally:
                    await self._waiting.pop(identifier)
            else:
                result = await self._waiting[identifier]
                if hook_on_cache:
                    for x in result:
                        yield hook_on_cache(x)
                else:
                    for x in result:
                        yield x

    async def _fetch(self, fut: Future,
                     remote_fetcher: Callable[[], Union[T, Awaitable[T]]],
                     cache_updater: Callable[[T], Awaitable[NoReturn]]):
        await self._semaphore.acquire()
        try:
            result = remote_fetcher()
            if isawaitable(result):
                result = await result

            await cache_updater(result)
            fut.set_result(result)
        except Exception as e:
            fut.set_exception(e)
        finally:
            self._semaphore.release()


__all__ = ("Mediator",)

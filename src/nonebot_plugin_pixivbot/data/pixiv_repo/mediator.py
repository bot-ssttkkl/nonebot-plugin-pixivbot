from asyncio import Future
from inspect import isawaitable
from typing import TypeVar, NoReturn, Optional, Any, Callable, Union, Awaitable, AsyncGenerator, List, Coroutine

from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import NoSuchItemError


class Mediator:
    def __init__(self):
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

            if hook_on_cache:
                cache = hook_on_cache(cache)
            return cache
        except NoSuchItemError:
            if identifier in self._waiting:
                return await self._waiting[identifier]

            fut = Future()
            self._waiting[identifier] = fut
            try:
                result = remote_fetcher()
                if isawaitable(result):
                    result = await result

                await cache_updater(result)

                if hook_on_fetch:
                    result = hook_on_fetch(result)
                fut.set_result(result)
                return result
            except Exception as e:
                fut.set_exception(e)
            finally:
                await self._waiting.pop(identifier)

    async def mixin_async_generator(self, identifier: Any,
                                    cache_loader: Callable[[], AsyncGenerator[T, None]],
                                    remote_fetcher: Callable[[], AsyncGenerator[T, None]],
                                    cache_updater: Callable[[List[T]], Coroutine[None, None, NoReturn]]) \
            -> AsyncGenerator[T, None]:
        try:
            async for x in cache_loader():
                yield x
        except NoSuchItemError:
            if identifier in self._waiting:
                result = await self._waiting[identifier]
                for x in result:
                    yield x
                return

            fut = Future()
            self._waiting[identifier] = fut
            try:
                result = []
                async for x in remote_fetcher():
                    result.append(x)
                    yield x

                await cache_updater(result)
                fut.set_result(result)
            except Exception as e:
                fut.set_exception(e)
            finally:
                await self._waiting.pop(identifier)

    async def mixin_append_async_generator(self, identifier: Any,
                                           cache_expired: bool,
                                           cache_loader: Callable[[], AsyncGenerator[T, None]],
                                           remote_fetcher: Callable[[], AsyncGenerator[T, None]],
                                           cache_checker: Callable[[List[T]], Awaitable[bool]],
                                           cache_updater: Callable[[List[T]], Coroutine[None, None, NoReturn]]) \
            -> AsyncGenerator[T, None]:
        # if cache expired, pick new bookmarks from remote
        if cache_expired:
            if identifier in self._waiting:
                await self._waiting[identifier]
            else:
                fut = Future()
                self._waiting[identifier] = fut

                try:
                    buffer = []
                    async for illust in remote_fetcher():
                        buffer.append(illust)
                        if len(buffer) >= 20:
                            exists = await cache_checker(buffer)
                            await cache_updater(buffer)

                            if exists:
                                break

                            buffer = []
                    else:
                        if len(buffer) > 0:
                            await cache_updater(buffer)
                    fut.set_result(1)
                except Exception as e:
                    fut.set_exception(e)
                finally:
                    await self._waiting.pop(identifier)

        async for x in cache_loader():
            yield x


__all__ = ("Mediator",)

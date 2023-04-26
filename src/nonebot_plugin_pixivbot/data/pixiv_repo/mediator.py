from datetime import datetime, timezone
from typing import List, AsyncGenerator, TypeVar, Union, Callable, Awaitable, Optional, Any, Mapping, Protocol, Generic

from nonebot import logger

from .errors import NoSuchItemError, CacheExpiredError
from .models import PixivRepoMetadata
from ...utils.format import format_kwargs

T = TypeVar("T")

T_KWARGS = Mapping[str, Any]


class Mediator(Protocol[T]):
    def mediate(self, query_kwargs: T_KWARGS, **kwargs) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
        ...


class SingleMediator(Mediator, Generic[T]):
    def __init__(self, tag: str,
                 cache_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 remote_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 cache_updater: Callable[[T_KWARGS, T, Optional[PixivRepoMetadata]], Awaitable[Any]]):
        self.tag = tag
        self.cache_factory = cache_factory
        self.remote_factory = remote_factory
        self.cache_updater = cache_updater

    async def mediate(self, query_kwargs: T_KWARGS,
                      *, force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
        try:
            if force_expiration:
                raise NoSuchItemError()
            async for x in self.cache_factory(query_kwargs):
                yield x
            logger.info(f"[{self.tag}] cache loaded  ({format_kwargs(**query_kwargs)})")
        except (NoSuchItemError, CacheExpiredError):
            logger.info(f"[{self.tag}] no cache or cache expired  ({format_kwargs(**query_kwargs)})")

            content = None
            metadata = None

            async for x in self.remote_factory(query_kwargs):
                if isinstance(x, PixivRepoMetadata):
                    metadata = x
                else:
                    content = x

            if metadata:
                # 先update再yield，受到SharedAsyncGeneratorManager的影响finally内的语句无法按时执行
                await self.cache_updater(query_kwargs, content, metadata)
                logger.info(f"[{self.tag}] cache updated  ({format_kwargs(**query_kwargs)})")

                yield metadata
                yield content

            else:
                raise RuntimeError("no metadata")


class ManyMediator(Mediator, Generic[T]):
    def __init__(self, tag: str,
                 cache_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 remote_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 cache_invalidator: Callable[[T_KWARGS], Awaitable[Any]],
                 cache_appender: Callable[[T_KWARGS, List[T], Optional[PixivRepoMetadata]], Awaitable[Any]]):
        self.tag = tag
        self.cache_factory = cache_factory
        self.remote_factory = remote_factory
        self.cache_invalidator = cache_invalidator
        self.cache_appender = cache_appender

    async def _load_many_from_local_and_remote_and_append(self, query_kwargs: T_KWARGS,
                                                          max_item: int,
                                                          max_page: int):
        loaded_items = 0
        loaded_pages = 0

        # first load from cache
        metadata = None
        async for x in self.cache_factory(query_kwargs):
            if isinstance(x, PixivRepoMetadata):
                metadata = x
                loaded_pages = metadata.pages
            else:
                loaded_items += 1

            yield x

            # check whether we approach limit
            if loaded_items >= max_item or loaded_pages >= max_page:
                break

        logger.info(f"[{self.tag}] cache loaded  ({format_kwargs(**query_kwargs)})")

        if loaded_items >= max_item or loaded_pages >= max_page:
            return

        # then check metadata["next_qs"] and load from remote
        if metadata and metadata.next_qs:
            async for x in self._load_many_from_remote_and_append(metadata.next_qs,
                                                                  max_item - loaded_items, max_page - loaded_pages,
                                                                  loaded_pages):
                yield x

    async def _load_many_from_remote_and_append(self, query_kwargs: T_KWARGS,
                                                max_item: int,
                                                max_page: int,
                                                metadata_page_offset: int = 0):
        loaded_items = 0
        loaded_pages = 0

        buffer = []

        async for item in self.remote_factory(query_kwargs):
            if isinstance(item, PixivRepoMetadata):
                item.pages += metadata_page_offset
                loaded_pages = item.pages

                if len(buffer) > 0:
                    await self.cache_appender(query_kwargs, buffer, item)
                    logger.info(f"[{self.tag}] cache appended  ({format_kwargs(**query_kwargs)})")

                    for x in buffer:
                        yield x

                    buffer.clear()

                    # check whether we approach limit
                    if loaded_items >= max_item or loaded_pages >= max_page:
                        return

                yield item
            else:
                loaded_items += 1
                buffer.append(item)

    async def mediate(self, query_kwargs: T_KWARGS,
                      *, force_expiration: bool = False,
                      max_item: int = 2 ** 31,
                      max_page: int = 2 ** 31, ) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
        try:
            if force_expiration:
                raise NoSuchItemError()

            async for x in self._load_many_from_local_and_remote_and_append(query_kwargs, max_item, max_page):
                yield x
        except NoSuchItemError:
            logger.info(f"[{self.tag}] no cache  ({format_kwargs(**query_kwargs)})")
            async for x in self._load_many_from_remote_and_append(query_kwargs, max_item, max_page):
                yield x
        except CacheExpiredError:
            logger.info(f"[{self.tag}] cache expired  ({format_kwargs(**query_kwargs)})")
            await self.cache_invalidator(query_kwargs)
            logger.info(f"[{self.tag}] cache invalidated  ({format_kwargs(**query_kwargs)})")
            async for x in self._load_many_from_remote_and_append(query_kwargs, max_item, max_page):
                yield x


class AppendMediator(ManyMediator):
    def __init__(self, tag: str,
                 cache_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 remote_factory: Callable[[T_KWARGS], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                 cache_invalidator: Callable[[T_KWARGS], Awaitable[Any]],
                 cache_appender: Callable[[T_KWARGS, List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
                 front_cache_appender: Callable[[T_KWARGS, List[T], Optional[PixivRepoMetadata]], Awaitable[bool]]):
        super().__init__(tag, cache_factory, remote_factory, cache_invalidator, cache_appender)
        self.front_cache_appender = front_cache_appender

    async def mediate(self, query_kwargs: Mapping[str, Any],
                      *, force_expiration: bool = False,
                      max_item: int = 2 ** 31,
                      max_page: int = 2 ** 31) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
        try:
            if force_expiration:
                metadata = None
                async for x in self.cache_factory(query_kwargs):
                    if isinstance(x, PixivRepoMetadata):
                        metadata = x
                        break

                if not metadata:
                    raise NoSuchItemError()
                else:
                    raise CacheExpiredError(metadata)

            async for x in self._load_many_from_local_and_remote_and_append(query_kwargs, max_item, max_page):
                yield x
        except NoSuchItemError:
            logger.info(f"[{self.tag}] no cache  ({format_kwargs(**query_kwargs)})")
            async for x in self._load_many_from_remote_and_append(query_kwargs, max_item, max_page):
                yield x
        except CacheExpiredError as e:
            logger.info(f"[{self.tag}] cache expired  ({format_kwargs(**query_kwargs)})")
            loaded_items = 0
            loaded_pages = 0

            # peek new bookmarks from remote
            # then append them to local cache until we found some items already exist
            buffer = []
            metadata = e.metadata

            async for x in self.remote_factory(query_kwargs):
                if isinstance(x, PixivRepoMetadata):
                    loaded_pages = x.pages
                    # we don't use this metadata

                    if len(buffer) > 0:
                        metadata.update_time = datetime.now(timezone.utc)
                        if await self.front_cache_appender(query_kwargs, buffer, metadata):
                            break
                        buffer = []

                        # check whether we approach limit
                        if loaded_items >= max_item or loaded_pages >= max_page:
                            return
                else:
                    loaded_items += 1
                    buffer.append(x)

            async for x in self._load_many_from_local_and_remote_and_append(query_kwargs, max_item, max_page):
                yield x


__all__ = ("SingleMediator", "ManyMediator", "AppendMediator")

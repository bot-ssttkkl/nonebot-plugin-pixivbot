from datetime import datetime, timezone
from typing import List, AsyncGenerator, TypeVar, Union, Callable, Awaitable, Optional, Any, Mapping

from nonebot import logger

from .errors import NoSuchItemError, CacheExpiredError
from .models import PixivRepoMetadata

T = TypeVar("T")


async def mediate_single(cache_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         query_kwargs: Mapping[str, Any],
                         cache_updater: Callable[[T, Optional[PixivRepoMetadata]], Awaitable[Any]],
                         force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            raise NoSuchItemError()
        async for x in cache_factory(**query_kwargs):
            yield x
    except (NoSuchItemError, CacheExpiredError):
        logger.info("[mediator] no cache or cache expired")

        content = None
        metadata = None

        async for x in remote_factory(**query_kwargs):
            if isinstance(x, PixivRepoMetadata):
                metadata = x
            else:
                content = x

        if metadata:
            # 先update再yield，受到SharedAsyncGeneratorManager的影响finally内的语句无法按时执行
            await cache_updater(content, metadata)

            yield metadata
            yield content

        else:
            raise RuntimeError("no metadata")


async def _load_many_from_local_and_remote_and_append(
        cache_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        query_kwargs: Mapping[str, Any],
        cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
        max_item: int,
        max_page: int):
    loaded_items = 0
    loaded_pages = 0

    # first load from cache
    metadata = None
    async for x in cache_factory(**query_kwargs):
        if isinstance(x, PixivRepoMetadata):
            metadata = x
            loaded_pages = metadata.pages
        else:
            loaded_items += 1

        yield x

        # check whether we approach limit
        if loaded_items >= max_item or loaded_pages >= max_page:
            return

    # then check metadata["next_qs"] and load from remote
    if metadata and metadata.next_qs:
        async for x in _load_many_from_remote_and_append(remote_factory, metadata.next_qs,
                                                         cache_appender,
                                                         max_item - loaded_items, max_page - loaded_pages,
                                                         loaded_pages):
            yield x


async def _load_many_from_remote_and_append(
        remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        query_kwargs: Mapping[str, Any],
        cache_appender: Callable[[T, Optional[PixivRepoMetadata]], Awaitable[Any]],
        max_item: int,
        max_page: int,
        metadata_page_offset: int = 0):
    loaded_items = 0
    loaded_pages = 0

    buffer = []

    async for item in remote_factory(**query_kwargs):
        if isinstance(item, PixivRepoMetadata):
            item.pages += metadata_page_offset
            loaded_pages = item.pages

            if len(buffer) > 0:
                await cache_appender(buffer, item)

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


async def mediate_many(cache_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                       remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                       query_kwargs: Mapping[str, Any],
                       cache_invalidator: Callable[[], Awaitable[Any]],
                       cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
                       max_item: int = 2 ** 31,
                       max_page: int = 2 ** 31,
                       force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            raise NoSuchItemError()

        async for x in _load_many_from_local_and_remote_and_append(cache_factory, remote_factory, query_kwargs,
                                                                   cache_appender, max_item, max_page):
            yield x
    except NoSuchItemError:
        logger.info("[mediator] no cache")
        async for x in _load_many_from_remote_and_append(remote_factory, query_kwargs,
                                                         cache_appender,
                                                         max_item, max_page):
            yield x
    except CacheExpiredError:
        logger.info("[mediator] cache expired")
        await cache_invalidator()
        async for x in _load_many_from_remote_and_append(remote_factory, query_kwargs,
                                                         cache_appender,
                                                         max_item, max_page):
            yield x


async def mediate_append(cache_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         query_kwargs: Mapping[str, Any],
                         cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[bool]],
                         max_item: int = 2 ** 31,
                         max_page: int = 2 ** 31,
                         force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            metadata = None
            async for x in cache_factory(**query_kwargs):
                if isinstance(x, PixivRepoMetadata):
                    metadata = x
                    break

            if not metadata:
                raise NoSuchItemError()
            else:
                raise CacheExpiredError(metadata)

        async for x in _load_many_from_local_and_remote_and_append(cache_factory, remote_factory, query_kwargs,
                                                                   cache_appender, max_item, max_page):
            yield x
    except NoSuchItemError:
        logger.info("[mediator] no cache")
        async for x in _load_many_from_remote_and_append(remote_factory, query_kwargs,
                                                         cache_appender,
                                                         max_item, max_page):
            yield x
    except CacheExpiredError as e:
        logger.info("[mediator] cache expired")
        loaded_items = 0
        loaded_pages = 0

        # peek new bookmarks from remote
        # then append them to local cache until we found some items already exist
        buffer = []
        metadata = e.metadata

        async for x in remote_factory(**query_kwargs):
            if isinstance(x, PixivRepoMetadata):
                loaded_pages = x.pages
                # we don't use this metadata

                if len(buffer) > 0:
                    metadata.update_time = datetime.now(timezone.utc)
                    if await cache_appender(buffer, metadata):
                        break
                    buffer = []

                    # check whether we approach limit
                    if loaded_items >= max_item or loaded_pages >= max_page:
                        return
            else:
                loaded_items += 1
                buffer.append(x)

        async for x in _load_many_from_local_and_remote_and_append(cache_factory, remote_factory, query_kwargs,
                                                                   cache_appender, max_item, max_page):
            yield x


__all__ = ("mediate_single", "mediate_many", "mediate_append")

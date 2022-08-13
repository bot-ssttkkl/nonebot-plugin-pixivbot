from datetime import datetime, timezone
from typing import List, AsyncGenerator, TypeVar, Union, Callable, Awaitable, Optional, Any

from .abstract_repo import PixivRepoMetadata
from .local_repo import NoSuchItemError, CacheExpiredError

T = TypeVar("T")


async def mediate_single(cache_factory: Callable[[], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         cache_updater: Callable[[T, Optional[PixivRepoMetadata]], Awaitable[Any]],
                         force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            raise NoSuchItemError()
        async for x in cache_factory():
            yield x
    except (NoSuchItemError, CacheExpiredError):
        content = None
        metadata = None

        async for x in remote_factory():
            if isinstance(x, PixivRepoMetadata):
                metadata = x
            else:
                content = x

        if metadata:
            try:
                yield metadata
                yield content
            finally:
                await cache_updater(content, metadata)
        else:
            raise RuntimeError("no metadata")


async def _load_many_from_local_and_remote_and_update(
        cache_factory: Callable[[], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
        max_item: int,
        max_page: int):
    loaded_items = 0
    loaded_pages = 0

    # first load from cache
    metadata = None
    async for x in cache_factory():
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
    # finally update local cache
    if metadata and metadata.next_qs:
        next_qs = metadata.next_qs
        content = []

        try:
            async for x in remote_factory(**next_qs):
                if isinstance(x, PixivRepoMetadata):
                    loaded_pages += 1
                    metadata = x
                    metadata.pages = loaded_pages
                else:
                    loaded_items += 1
                    content.append(x)

                yield x

                # check whether we approach limit
                if loaded_items >= max_item or loaded_pages >= max_page:
                    return
        finally:
            if metadata:
                await cache_appender(content, metadata)


async def _load_many_from_remote_and_update(
        remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
        cache_updater: Callable[[T, Optional[PixivRepoMetadata]], Awaitable[Any]],
        max_item: int,
        max_page: int):
    loaded_items = 0
    loaded_pages = 0

    # load from remote and update local cache
    content = []
    metadata = None

    try:
        async for x in remote_factory():
            if isinstance(x, PixivRepoMetadata):
                loaded_pages += 1
                metadata = x
                metadata.pages = loaded_pages
            else:
                loaded_items += 1
                content.append(x)

            yield x

            # check whether we approach limit
            if loaded_items >= max_item or loaded_pages >= max_page:
                return
    finally:
        if metadata:
            await cache_updater(content, metadata)


async def mediate_many(cache_factory: Callable[[], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                       remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                       cache_updater: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
                       cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
                       max_item: int = 2 ** 31,
                       max_page: int = 2 ** 31,
                       force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            raise NoSuchItemError()

        async for x in _load_many_from_local_and_remote_and_update(cache_factory, remote_factory, cache_appender,
                                                                   max_item, max_page):
            yield x
    except (CacheExpiredError, NoSuchItemError):
        async for x in _load_many_from_remote_and_update(remote_factory, cache_updater,
                                                         max_item, max_page):
            yield x


async def mediate_append(cache_factory: Callable[[], AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         remote_factory: Callable[..., AsyncGenerator[Union[T, PixivRepoMetadata], None]],
                         cache_updater: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[Any]],
                         cache_appender: Callable[[List[T], Optional[PixivRepoMetadata]], Awaitable[bool]],
                         max_item: int = 2 ** 31,
                         max_page: int = 2 ** 31,
                         force_expiration: bool = False) -> AsyncGenerator[Union[T, PixivRepoMetadata], None]:
    try:
        if force_expiration:
            metadata = None
            async for x in cache_factory():
                if isinstance(x, PixivRepoMetadata):
                    metadata = x
                    break

            if not metadata:
                raise NoSuchItemError()
            else:
                raise CacheExpiredError(metadata)

        async for x in _load_many_from_local_and_remote_and_update(cache_factory, remote_factory, cache_appender,
                                                                   max_item, max_page):
            yield x
    except NoSuchItemError:
        async for x in _load_many_from_remote_and_update(remote_factory, cache_updater,
                                                         max_item, max_page):
            yield x
    except CacheExpiredError as e:
        loaded_items = 0
        loaded_pages = 0

        # peek new bookmarks from remote
        # then append them to local cache until we found some items already exist
        buffer = []
        metadata = e.metadata

        async for x in remote_factory():
            if isinstance(x, PixivRepoMetadata):
                loaded_pages += 1
                # we don't use this metadata
            else:
                loaded_items += 1
                buffer.append(x)

            if len(buffer) >= 20:
                metadata.update_time = datetime.now(timezone.utc)
                if await cache_appender(buffer, metadata):
                    break
                buffer = []

            # check whether we approach limit
            if loaded_items >= max_item or loaded_pages >= max_page:
                return
        else:
            if len(buffer) > 0:
                metadata.update_time = datetime.now(timezone.utc)
                await cache_appender(buffer, metadata)

        async for x in _load_many_from_local_and_remote_and_update(cache_factory, remote_factory, cache_appender,
                                                                   max_item, max_page):
            yield x


__all__ = ("mediate_single", "mediate_many", "mediate_append")

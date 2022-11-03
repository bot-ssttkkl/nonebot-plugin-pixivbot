from asyncio import sleep
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from tests import MyTest


class TestMediateSingle(MyTest):
    @pytest.fixture
    def cache_factory_with_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0))

        async def agen():
            await sleep(0.1)
            yield cache_metadata
            yield "cache"

        return agen

    @pytest.fixture
    def cache_factory_with_expired_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.errors import CacheExpiredError

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0))

        async def agen():
            await sleep(0.1)
            raise CacheExpiredError(cache_metadata)
            # noinspection PyUnreachableCode
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def remote_factory(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        async def remote_factory():
            await sleep(0.2)
            yield PixivRepoMetadata()
            yield "remote"

        return remote_factory

    @pytest.mark.asyncio
    async def test_with_cache(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_single

        cache_updater = AsyncMock()

        content = None
        metadata = None
        # noinspection PyTypeChecker
        async for x in mediate_single(cache_factory_with_cache, remote_factory, {}, cache_updater):
            if isinstance(x, PixivRepoMetadata):
                metadata = x
            else:
                content = x

        assert content == "cache"
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_updater.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_expired_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_single

        cache_updater = AsyncMock()

        content = None
        metadata = None
        # noinspection PyTypeChecker
        async for x in mediate_single(cache_factory_with_expired_cache, remote_factory, {}, cache_updater):
            if isinstance(x, PixivRepoMetadata):
                metadata = x
            else:
                content = x

        assert content == "remote"
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_updater.assert_awaited_once_with(content, metadata)


class TestMediateCollection(MyTest):
    @pytest.fixture
    def cache_factory_with_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={"next": 30})

        async def agen():
            await sleep(0.1)

            cache_metadata.pages = 0
            yield cache_metadata

            for i in range(30):
                yield i

            cache_metadata.pages = 5
            yield cache_metadata

            # meta, 0, 1, ..., 29

        return agen

    @pytest.fixture
    def cache_factory_with_cache_and_empty_next_qs(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={})

        async def agen():
            await sleep(0.1)

            cache_metadata.pages = 0
            yield cache_metadata

            for i in range(30):
                yield i

            cache_metadata.pages = 5
            yield cache_metadata

            # meta, 0, 1, ..., 29

        return agen

    @pytest.fixture
    def cache_factory_with_no_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.errors import NoSuchItemError

        async def agen():
            await sleep(0.1)
            raise NoSuchItemError()
            # noinspection PyUnreachableCode
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def cache_factory_with_expired_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.errors import CacheExpiredError

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={"next": 30})

        async def agen():
            await sleep(0.1)
            raise CacheExpiredError(cache_metadata)
            # noinspection PyUnreachableCode
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def remote_factory(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        async def remote_factory(next=0):
            await sleep(0.1)
            yield PixivRepoMetadata(pages=0, next_qs={"next": next})

            for i in range(1, 4):
                for j in range(20):
                    yield next
                    next += 1
                yield PixivRepoMetadata(pages=i, next_qs={"next": next})

            # next=0: meta, 0, 1, ..., 19, meta, 20, 21, ..., 39, meta, 40, 41, ..., 59, meta
            # next=30: meta, 30, 31, ..., 49, meta, 50, 51, ..., 69, meta, 70, 71, ..., 89, meta

        return remote_factory


class TestMediateMany(TestMediateCollection):
    @pytest.mark.asyncio
    async def test_with_cache_and_empty_next_qs(self, cache_factory_with_cache_and_empty_next_qs, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_invalidator = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        # noinspection PyTypeChecker
        async for x in mediate_many(cache_factory_with_cache_and_empty_next_qs, remote_factory, {},
                                    cache_invalidator, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(30)]
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_invalidator.assert_not_awaited()
        cache_appender.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_cache_and_remote(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_invalidator = AsyncMock()
        cache_appender_calls = []

        async def cache_appender(items, metadata):
            cache_appender_calls.append((list(items), metadata))

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_cache, remote_factory, {},
                                    cache_invalidator, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(90)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_invalidator.assert_not_awaited()
        assert cache_appender_calls == [
            ([x for x in range(30, 50)], PixivRepoMetadata(pages=6, next_qs={"next": 50})),
            ([x for x in range(50, 70)], PixivRepoMetadata(pages=7, next_qs={"next": 70})),
            ([x for x in range(70, 90)], PixivRepoMetadata(pages=8, next_qs={"next": 90})),
        ]

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_no_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_invalidator = AsyncMock()
        cache_appender_calls = []

        async def cache_appender(items, metadata):
            cache_appender_calls.append((list(items), metadata))

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_no_cache, remote_factory, {},
                                    cache_invalidator, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(60)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_invalidator.assert_not_awaited()
        assert cache_appender_calls == [
            ([x for x in range(0, 20)], PixivRepoMetadata(pages=1, next_qs={"next": 20})),
            ([x for x in range(20, 40)], PixivRepoMetadata(pages=2, next_qs={"next": 40})),
            ([x for x in range(40, 60)], PixivRepoMetadata(pages=3, next_qs={"next": 60})),
        ]

    @pytest.mark.asyncio
    async def test_with_expired_cache_and_remote(self, cache_factory_with_expired_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_invalidator = AsyncMock()
        cache_appender_calls = []

        async def cache_appender(items, metadata):
            cache_appender_calls.append((list(items), metadata))

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_expired_cache, remote_factory, {},
                                    cache_invalidator, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(60)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_invalidator.assert_awaited_once()
        assert cache_appender_calls == [
            ([x for x in range(0, 20)], PixivRepoMetadata(pages=1, next_qs={"next": 20})),
            ([x for x in range(20, 40)], PixivRepoMetadata(pages=2, next_qs={"next": 40})),
            ([x for x in range(40, 60)], PixivRepoMetadata(pages=3, next_qs={"next": 60})),
        ]


class TestMediateAppend(TestMediateCollection):
    @pytest.mark.asyncio
    async def test_with_cache_and_empty_next_qs(self, cache_factory_with_cache_and_empty_next_qs, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_appender = AsyncMock()

        items = []
        metadata = None
        # noinspection PyTypeChecker
        async for x in mediate_append(cache_factory_with_cache_and_empty_next_qs, remote_factory, {}, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(30)]
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_appender.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_cache_and_remote(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_appender_calls = []

        async def cache_appender(items, metadata):
            cache_appender_calls.append((list(items), metadata))

        items = []
        metadata = None
        async for x in mediate_append(cache_factory_with_cache, remote_factory, {}, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(90)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        assert cache_appender_calls == [
            ([x for x in range(30, 50)], PixivRepoMetadata(pages=6, next_qs={"next": 50})),
            ([x for x in range(50, 70)], PixivRepoMetadata(pages=7, next_qs={"next": 70})),
            ([x for x in range(70, 90)], PixivRepoMetadata(pages=8, next_qs={"next": 90})),
        ]

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_no_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_appender_calls = []

        async def cache_appender(items, metadata):
            cache_appender_calls.append((list(items), metadata))

        items = []
        metadata = None
        async for x in mediate_append(cache_factory_with_no_cache, remote_factory, {}, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(60)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        assert cache_appender_calls == [
            ([x for x in range(0, 20)], PixivRepoMetadata(pages=1, next_qs={"next": 20})),
            ([x for x in range(20, 40)], PixivRepoMetadata(pages=2, next_qs={"next": 40})),
            ([x for x in range(40, 60)], PixivRepoMetadata(pages=3, next_qs={"next": 60})),
        ]

    @pytest.mark.asyncio
    async def test_with_expired_cache(self, cache_factory_with_cache,
                                      cache_factory_with_expired_cache,
                                      remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepoMetadata

        cache_updated = False

        def cache_factory():
            if not cache_updated:
                return cache_factory_with_expired_cache()
            else:
                return cache_factory_with_cache()

        cache_appender_calls = []

        async def cache_appender(items, metadata):
            nonlocal cache_updated
            cache_updated = True
            cache_appender_calls.append((list(items), metadata))
            return True

        items = []
        metadata = []
        async for x in mediate_append(cache_factory, remote_factory, {}, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata.append(x)

        assert items == [x for x in range(90)]
        assert metadata[0].update_time == datetime.fromtimestamp(0)  # assert the first metadata comes from cache
        assert metadata[-1].update_time != datetime.fromtimestamp(0)  # assert the last metadata comes from remote

        # assert the first call for peek remote update with updated metadata
        assert cache_appender_calls[0][0] == [x for x in range(20)]
        assert cache_appender_calls[0][1].next_qs == metadata[0].next_qs

        # assert the second call for append remote data
        assert cache_appender_calls[1:] == [
            ([x for x in range(30, 50)], PixivRepoMetadata(pages=6, next_qs={"next": 50})),
            ([x for x in range(50, 70)], PixivRepoMetadata(pages=7, next_qs={"next": 70})),
            ([x for x in range(70, 90)], PixivRepoMetadata(pages=8, next_qs={"next": 90})),
        ]

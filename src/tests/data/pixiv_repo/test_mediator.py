from asyncio import sleep
from datetime import datetime
from unittest.mock import AsyncMock, call

import pytest

from tests import MyTest


class TestMediateSingle(MyTest):
    @pytest.fixture
    def cache_factory_with_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0))

        async def agen():
            await sleep(0.1)
            yield cache_metadata
            yield "cache"

        return agen

    @pytest.fixture
    def cache_factory_with_expired_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.local_repo import CacheExpiredError

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0))

        async def agen():
            await sleep(0.1)
            raise CacheExpiredError(cache_metadata)
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def remote_factory(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        async def remote_factory():
            await sleep(0.2)
            yield PixivRepoMetadata()
            yield "remote"

        return remote_factory

    @pytest.mark.asyncio
    async def test_with_cache(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_single

        cache_updater = AsyncMock()

        content = None
        metadata = None
        async for x in mediate_single(cache_factory_with_cache, remote_factory, cache_updater):
            if isinstance(x, PixivRepoMetadata):
                metadata = x
            else:
                content = x

        assert content == "cache"
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_updater.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_expired_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_single

        cache_updater = AsyncMock()

        content = None
        metadata = None
        async for x in mediate_single(cache_factory_with_expired_cache, remote_factory, cache_updater):
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
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={"next": 30})

        async def agen():
            await sleep(0.1)
            yield cache_metadata
            for i in range(30):
                yield i

            # meta, 0, 1, ..., 29

        return agen

    @pytest.fixture
    def cache_factory_with_cache_and_empty_next_qs(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={})

        async def agen():
            await sleep(0.1)
            yield cache_metadata
            for i in range(30):
                yield i

            # meta, 0, 1, ..., 29

        return agen

    @pytest.fixture
    def cache_factory_with_no_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.local_repo import NoSuchItemError

        async def agen():
            await sleep(0.1)
            raise NoSuchItemError()
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def cache_factory_with_expired_cache(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata
        from nonebot_plugin_pixivbot.data.pixiv_repo.local_repo import CacheExpiredError

        cache_metadata = PixivRepoMetadata(update_time=datetime.fromtimestamp(0),
                                           pages=5,
                                           next_qs={"next": 30})

        async def agen():
            await sleep(0.1)
            raise CacheExpiredError(cache_metadata)
            yield None  # to mark it as an AsyncGenerator

        return agen

    @pytest.fixture
    def remote_factory(self):
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

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
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_cache_and_empty_next_qs, remote_factory,
                                    cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(30)]
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_updater.assert_not_awaited()
        cache_appender.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_cache_and_remote(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_cache, remote_factory,
                                    cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(90)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_updater.assert_not_awaited()
        cache_appender.assert_awaited_once_with([x for x in range(30, 90)], metadata)

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_no_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_many
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_many(cache_factory_with_no_cache, remote_factory,
                                    cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(60)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_updater.assert_awaited_once_with([x for x in range(60)], metadata)
        cache_appender.assert_not_awaited()


class TestMediateAppend(TestMediateCollection):
    @pytest.mark.asyncio
    async def test_with_cache_and_empty_next_qs(self, cache_factory_with_cache_and_empty_next_qs, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_append(cache_factory_with_cache_and_empty_next_qs, remote_factory,
                                      cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(30)]
        assert metadata.update_time == datetime.fromtimestamp(0)  # assert metadata comes from cache
        cache_updater.assert_not_awaited()
        cache_appender.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_cache_and_remote(self, cache_factory_with_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_append(cache_factory_with_cache, remote_factory,
                                      cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(90)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_updater.assert_not_awaited()
        cache_appender.assert_awaited_once_with([x for x in range(30, 90)], metadata)

    @pytest.mark.asyncio
    async def test_with_remote(self, cache_factory_with_no_cache, remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updater = AsyncMock()
        cache_appender = AsyncMock()

        items = []
        metadata = None
        async for x in mediate_append(cache_factory_with_no_cache, remote_factory,
                                      cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata = x

        assert items == [x for x in range(60)]
        assert metadata.update_time != datetime.fromtimestamp(0)  # assert metadata comes from remote
        cache_updater.assert_awaited_once_with([x for x in range(60)], metadata)
        cache_appender.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_with_expired_cache(self, cache_factory_with_cache,
                                      cache_factory_with_expired_cache,
                                      remote_factory):
        from nonebot_plugin_pixivbot.data.pixiv_repo.mediator import mediate_append
        from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata

        cache_updated = False

        def cache_factory():
            if not cache_updated:
                return cache_factory_with_expired_cache()
            else:
                return cache_factory_with_cache()

        async def cache_appender(items, metadata):
            nonlocal cache_updated

            await sleep(0.1)
            cache_updated = True
            return True

        cache_updater = AsyncMock()
        cache_appender = AsyncMock(side_effect=cache_appender)

        items = []
        metadata = []
        async for x in mediate_append(cache_factory, remote_factory,
                                      cache_updater, cache_appender):
            if not isinstance(x, PixivRepoMetadata):
                items.append(x)
            else:
                metadata.append(x)

        assert items == [x for x in range(90)]
        assert metadata[0].update_time == datetime.fromtimestamp(0)  # assert the first metadata comes from cache
        assert metadata[-1].update_time != datetime.fromtimestamp(0)  # assert the last metadata comes from remote
        cache_updater.assert_not_awaited()

        # assert the first call for peek remote update with updated metadata
        assert cache_appender.await_args_list[0].args[0] == [x for x in range(20)]
        assert cache_appender.await_args_list[0].args[1].next_qs == metadata[0].next_qs

        # assert the second call for append remote data
        assert cache_appender.await_args_list[1] == call([x for x in range(30, 90)], metadata[-1])

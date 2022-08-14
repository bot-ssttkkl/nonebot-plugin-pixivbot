from asyncio import sleep, create_task, gather
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, call

import pytest

from tests import MyTest


class TestSharedAsyncGeneratorContextManager(MyTest):
    @pytest.fixture
    def origin_agen(self):
        cnt = 0

        async def agen():
            nonlocal cnt
            for i in range(10):
                await sleep(0.1)
                yield cnt
                cnt += 1

        return agen()

    @pytest.fixture
    def ctx_mgr(self, origin_agen):
        from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorContextManager

        on_each = AsyncMock()
        on_stop = AsyncMock()
        on_consumers_changed = MagicMock()

        return SharedAsyncGeneratorContextManager(
            origin_agen,
            on_each,
            on_stop,
            on_consumers_changed
        )

    @pytest.mark.asyncio
    async def test_on_each_and_on_stop(self, origin_agen):
        from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorContextManager

        on_each = AsyncMock()
        on_stop = AsyncMock()
        on_consumers_changed = MagicMock()

        ctx_mgr = SharedAsyncGeneratorContextManager(
            origin_agen,
            on_each,
            on_stop,
            on_consumers_changed
        )

        with ctx_mgr as iter:
            items = [i async for i in iter]

        on_each.assert_has_awaits([call(i) for i in range(10)])
        on_stop.assert_awaited_once_with([i for i in range(10)])

    @pytest.mark.asyncio
    async def test_single_consumer(self, ctx_mgr):
        with ctx_mgr as iter:
            items = [i async for i in iter]

        assert items == [i for i in range(10)]

        # noinspection PyUnresolvedReferences
        ctx_mgr._on_consumers_changed.assert_has_calls([call(ctx_mgr, 1), call(ctx_mgr, 0)])

    @pytest.mark.asyncio
    async def test_multi_consumer(self, ctx_mgr):
        async def consume():
            with ctx_mgr as iter:
                items = [i async for i in iter]

            assert items == [i for i in range(10)]

        # consumer2 except to wait for all the 10 items together
        consumer1 = create_task(consume())
        await sleep(0.25)

        # consumer2 except to get 2 generated items, then wait for the rest 8 items together
        consumer2 = create_task(consume())

        # consumer3 begin collecting after the agen stopped
        await sleep(1.5)
        consumer3 = create_task(consume())

        await gather(consumer1, consumer2, consumer3)

        # noinspection PyUnresolvedReferences
        ctx_mgr._on_consumers_changed.assert_has_calls(
            [call(ctx_mgr, 1), call(ctx_mgr, 2), call(ctx_mgr, 1), call(ctx_mgr, 0), call(ctx_mgr, 1),
             call(ctx_mgr, 0)])

    @pytest.mark.asyncio
    async def test_close(self, ctx_mgr):
        with ctx_mgr as iter:
            await iter.__anext__()
            await iter.__anext__()

        ctx_mgr.close()

        with ctx_mgr as iter:
            await iter.__anext__()
            await iter.__anext__()
            with pytest.raises(StopAsyncIteration):
                await iter.__anext__()


class TestSharedAsyncGeneratorManager(MyTest):
    @pytest.fixture
    def shared_agen_mgr(self):
        from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager

        class SharedAsyncGeneratorManagerImpl(SharedAsyncGeneratorManager[int, int]):
            def agen_factory(self, identifier: int, *args, **kwargs) -> AsyncGenerator[int, None]:
                async def agen():
                    cnt = identifier
                    for i in range(10):
                        await sleep(0.1)
                        yield cnt
                        cnt += 1

                return agen()

        impl = SharedAsyncGeneratorManagerImpl()
        impl.on_agen_next = AsyncMock()
        impl.on_agen_stop = AsyncMock()
        return impl

    @pytest.mark.asyncio
    async def test_get(self, shared_agen_mgr):
        # except same
        inst = shared_agen_mgr.get(0)
        with inst as iter:
            inst2 = shared_agen_mgr.get(0)
            with inst2 as iter2:
                assert inst == inst2

        # prev inst was except to be destroyed

        inst3 = shared_agen_mgr.get(0)
        assert inst != inst3

    @pytest.mark.asyncio
    async def test_set_expires_time(self, shared_agen_mgr):
        inst = shared_agen_mgr.get(0)
        with inst as iter:
            await iter.__anext__()
            await iter.__anext__()

            shared_agen_mgr.set_expires_time(0, datetime.now(timezone.utc) + timedelta(seconds=1))

        # prev inst was except to be saved

        inst2 = shared_agen_mgr.get(0)
        assert inst == inst2

        await sleep(1.5)

        # prev inst was except to be removed

        inst2 = shared_agen_mgr.get(0)
        assert inst != inst2

    @pytest.mark.asyncio
    async def test_invalidate(self, shared_agen_mgr):
        inst = shared_agen_mgr.get(0)
        with inst as iter:
            await iter.__anext__()
            await iter.__anext__()

            shared_agen_mgr.set_expires_time(0, datetime.now(timezone.utc) + timedelta(seconds=1))

        # prev inst was except to be saved

        inst2 = shared_agen_mgr.get(0)
        assert inst == inst2

        shared_agen_mgr.invalidate(0)

        # prev inst was except to be removed

        inst2 = shared_agen_mgr.get(0)
        assert inst != inst2

        # invalidate a non-existing key should not raise
        shared_agen_mgr.invalidate(114514)
from asyncio import sleep, create_task, gather
from unittest.mock import Mock, MagicMock, AsyncMock, call

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
        from nonebot_plugin_pixivbot.data.pixiv_repo.shared_agen import SharedAsyncGeneratorContextManager

        on_each = AsyncMock()
        on_stop = AsyncMock()
        on_consumers_changed = MagicMock()

        yield SharedAsyncGeneratorContextManager(
            origin_agen,
            on_each,
            on_stop,
            on_consumers_changed
        )

        on_each.assert_has_awaits([call(i) for i in range(10)])
        on_stop.assert_awaited_once_with([i for i in range(10)])

    @pytest.mark.asyncio
    async def test_single_consumer(self, ctx_mgr):
        with ctx_mgr as iter:
            items = [i async for i in iter]

        assert items == [i for i in range(10)]

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

        ctx_mgr._on_consumers_changed.assert_has_calls(
            [call(ctx_mgr, 1), call(ctx_mgr, 2), call(ctx_mgr, 1), call(ctx_mgr, 0), call(ctx_mgr, 1), call(ctx_mgr, 0)])

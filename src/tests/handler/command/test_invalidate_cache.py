import pytest

from tests.data.pixiv_repo.fake_pixiv_repo import FakePixivRepoMixin
from tests.handler.common import HandlerTester


class TestInvalidateCache(HandlerTester,
                          FakePixivRepoMixin):
    except_msg = "ok"

    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command import InvalidateCacheHandler
        return InvalidateCacheHandler

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivRepo):
        from nonebot_plugin_pixivbot.global_context import context

        await tester()

        context.require(FakePixivRepo).invalidate_cache.has_awaited()

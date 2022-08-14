from unittest.mock import AsyncMock

import pytest

from tests import MyTest
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin


class TestInvalidateCache(FakePostDestinationMixin,
                          FakePostmanManagerMixin,
                          MyTest):
    @pytest.fixture
    def fake_pixiv_repo(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo

        @context.bind_singleton_to(PixivRepo)
        class PixivRepo:
            invalidate_cache = AsyncMock()

        return PixivRepo

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_repo, fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import InvalidateCacheHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "ok"

        await context.require(InvalidateCacheHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        context.require(fake_pixiv_repo).invalidate_cache.has_awaited()

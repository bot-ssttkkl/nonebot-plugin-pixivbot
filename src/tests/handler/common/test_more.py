from unittest.mock import AsyncMock

import pytest

from tests.handler.common import HandlerTester
from tests.handler.common.fake_recorder import FakeRecorderMixin


class MoreHandlerTester(HandlerTester,
                        FakeRecorderMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import MoreHandler
        return MoreHandler


class TestMoreHandle(MoreHandlerTester):
    kwargs = {"count": 3}

    @pytest.mark.asyncio
    async def test(self, tester,
                   FakeRecorder,
                   FakePostDestination):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.handler.recorder import Req

        post_dest = FakePostDestination(123456, 56789)
        stub = AsyncMock()
        context.require(FakeRecorder).record_req(Req(stub, 114, 514), post_dest.identifier)

        await tester(post_dest=post_dest)
        stub.assert_awaited_once_with(114, 514, count=3, post_dest=post_dest, silently=False)


class TestMoreHandleNoRecord(MoreHandlerTester):
    kwargs = {"count": 3}

    @pytest.mark.asyncio
    async def test(self, tester,
                   FakePostDestination):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        post_dest = FakePostDestination(123456, 56789)

        with pytest.raises(BadRequestError) as e:
            await tester(post_dest=post_dest)
        assert e.value.message == "你还没有发送过请求"

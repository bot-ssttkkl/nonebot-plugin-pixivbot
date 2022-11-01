import pytest

from tests.handler.common import HandlerTester
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin


class UnBindHandlerTester(HandlerTester,
                          FakePixivAccountBinderMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.bind import UnbindHandler
        return UnbindHandler


class TestUnbindHandlerBind(UnBindHandlerTester):
    args = []
    except_msg = "Pixiv账号解绑成功"

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivAccountBinder):
        from nonebot_plugin_pixivbot import context

        await context.require(FakePixivAccountBinder).bind(adapter="test",
                                                           user_id=1234,
                                                           pixiv_user_id=123321)

        await tester()

        assert ("test", 1234) not in context.require(FakePixivAccountBinder).bindings


class TestUnbindHandlerNotBind(UnBindHandlerTester):
    args = []
    except_msg = "当前未绑定Pixiv账号"

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivAccountBinder):
        from nonebot_plugin_pixivbot import context

        await tester()

        assert ("test", 1234) not in context.require(FakePixivAccountBinder).bindings

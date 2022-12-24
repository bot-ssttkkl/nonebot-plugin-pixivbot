import pytest

from tests.handler.common import HandlerTester
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin


class BindHandlerTester(HandlerTester,
                        FakePixivAccountBinderMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.bind import BindHandler
        return BindHandler


class TestBindHandlerNoArg(BindHandlerTester):
    except_msg = "当前未绑定Pixiv账号\n命令格式：/pixivbot bind <pixiv_user_id>"


class TestBindHandlerBind(BindHandlerTester):
    args = ["123321"]
    except_msg = "Pixiv账号绑定成功"

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivAccountBinder):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.model import PixivBinding

        await tester()

        assert context.require(FakePixivAccountBinder).bindings[("test", 1234)] == PixivBinding(adapter="test",
                                                                                                user_id=1234,
                                                                                                pixiv_user_id=123321)


class TestBindHandlerInvalidArg(BindHandlerTester):
    args = ["invalid_arg_lol"]
    except_msg = "请输入正确格式的Pixiv账号"

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivAccountBinder):
        from nonebot_plugin_pixivbot.global_context import context

        await tester()

        assert ("test", 1234) not in context.require(FakePixivAccountBinder).bindings

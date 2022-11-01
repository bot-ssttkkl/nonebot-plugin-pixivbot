import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class IllustHandlerTester(HandlerTester,
                          FakePixivServiceMixin,
                          MockMessageModelMixin, ):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import IllustHandler
        return IllustHandler


class TestIllustHandle(IllustHandlerTester):
    args = ["123456"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService,
                   mock_illust_message_model):
        from nonebot_plugin_pixivbot import context

        async def except_message():
            illusts = context.require(FakePixivService).spy_illust_detail.spy_return
            return await mock_illust_message_model(illusts)

        await tester(except_msg=except_message)


class TestIllustHandleNoData(IllustHandlerTester):
    args = ["123456"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService,
                   mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        with pytest.raises(QueryError):
            await tester()


class TestIllustHandleInvalidArg(IllustHandlerTester):
    args = ["abcdef"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService,
                   mock_illust_message_model):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "abcdef不是合法的插画ID"

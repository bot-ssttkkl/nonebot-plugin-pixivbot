import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomIllustHandlerTester(HandlerTester,
                                FakePixivServiceMixin,
                                MockMessageModelMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RandomIllustHandler
        return RandomIllustHandler


class TestRandomIllustHandle(RandomIllustHandlerTester):
    args = ["some_word"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            illusts = context.require(FakePixivService).spy_random_illust.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的some_word图")

        await tester(except_msg=except_message)


class TestRandomIllustHandleNoData(RandomIllustHandlerTester):
    args = ["some_word"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        with pytest.raises(QueryError) as e:
            await tester()

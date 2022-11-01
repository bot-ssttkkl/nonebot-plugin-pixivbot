import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomRecommendedIllustHandlerTester(HandlerTester,
                                           FakePixivServiceMixin,
                                           MockMessageModelMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RandomRecommendedIllustHandler
        return RandomRecommendedIllustHandler


class TestRandomRecommendedIllustHandle(RandomRecommendedIllustHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            illusts = context.require(FakePixivService).spy_random_recommended_illust.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的图")

        await tester(except_msg=except_message)


class TestRandomRecommendedIllustHandleNoData(RandomRecommendedIllustHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        with pytest.raises(QueryError) as e:
            await tester()

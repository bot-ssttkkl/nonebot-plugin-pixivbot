import pytest

from tests.handler.common import HandlerTester
from tests.handler.common.fake_recorder import FakeRecorderMixin
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomRelatedIllustHandlerTester(HandlerTester,
                                       FakePixivServiceMixin,
                                       MockMessageModelMixin,
                                       FakeRecorderMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RandomRelatedIllustHandler
        return RandomRelatedIllustHandler


class TestRandomRecommendedIllustHandle(RandomRelatedIllustHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService, FakeRecorder, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = FakePostDestination(123456, 56789)
        context.require(FakeRecorder).record_resp(114514, post_dest.identifier)

        async def except_message():
            illusts = context.require(FakePixivService).spy_random_related_illust.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的[114514]的相关图片")

        await tester(post_dest=post_dest, except_msg=except_message)


class TestRandomRecommendedIllustHandleNoData(RandomRelatedIllustHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService, FakeRecorder, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        post_dest = FakePostDestination(123456, 56789)
        context.require(FakeRecorder).record_resp(114514, post_dest.identifier)

        with pytest.raises(QueryError) as e:
            await tester(post_dest=post_dest)


class TestRandomRecommendedIllustHandleNoRecord(RandomRelatedIllustHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "你还没有发送过请求"

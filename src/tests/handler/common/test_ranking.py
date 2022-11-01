import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomRankingHandlerTester(HandlerTester,
                                 FakePixivServiceMixin,
                                 MockMessageModelMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RankingHandler
        return RankingHandler


class TestRankingHandle(RandomRankingHandlerTester):
    args = ["day", "1-3"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            illusts = context.require(FakePixivService).spy_illust_ranking.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的日榜", number=1)

        await tester(except_msg=except_message)


class TestRankingHandleWithoutRange(RandomRankingHandlerTester):
    args = ["day"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            illusts = context.require(FakePixivService).spy_illust_ranking.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的日榜", number=1)

        await tester(except_msg=except_message)


class TestRankingInvalidArg1(RandomRankingHandlerTester):
    args = ["abcdef"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "abcdef不是合法的榜单类型"


class TestRankingInvalidArg2(RandomRankingHandlerTester):
    args = ["day", "abcdef"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "abcdef不是合法的范围"

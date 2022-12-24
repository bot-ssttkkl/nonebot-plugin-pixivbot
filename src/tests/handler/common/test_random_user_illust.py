import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomUserIllustHandlerTester(HandlerTester,
                                    FakePixivServiceMixin,
                                    MockMessageModelMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RandomUserIllustHandler
        return RandomUserIllustHandler


class TestRandomUserIllustHandle(RandomUserIllustHandlerTester):
    args = ["54321"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            user, illusts = context.require(FakePixivService).spy_random_user_illust.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header=f"这是您点的{user.name}({user.id})老师的图")

        await tester(except_msg=except_message)


class TestRandomUserIllustHandleByName(RandomUserIllustHandlerTester):
    args = ["TestUser"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        async def except_message():
            user, illusts = context.require(FakePixivService).spy_random_user_illust.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header=f"这是您点的{user.name}({user.id})老师的图")

        await tester(except_msg=except_message)


class TestRandomUserIllustHandleNoData(RandomUserIllustHandlerTester):
    args = ["54321"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        with pytest.raises(QueryError) as e:
            await tester()

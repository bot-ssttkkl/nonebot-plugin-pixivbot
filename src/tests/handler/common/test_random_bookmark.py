import pytest

from tests.handler.common import HandlerTester
from tests.model.mock_message import MockMessageModelMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class RandomBookmarkHandlerTester(HandlerTester,
                                  FakePixivServiceMixin,
                                  MockMessageModelMixin,
                                  FakePixivAccountBinderMixin):
    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler
        return RandomBookmarkHandler


class TestRandomBookmarkHandle(RandomBookmarkHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService,
                   mock_illust_message_model,
                   FakePostDestination,
                   FakePixivAccountBinder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = FakePostDestination(123456, 56789)
        await context.require(FakePixivAccountBinder).bind(post_dest.adapter, post_dest.user_id, 54321)

        async def except_message():
            illusts = context.require(FakePixivService).spy_random_bookmark.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的私家车")

        await tester(post_dest=post_dest, except_msg=except_message)


class TestRandomBookmarkHandleNotBind(RandomBookmarkHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "无效的Pixiv账号，或未绑定Pixiv账号"


class TestRandomBookmarkHandleArg(RandomBookmarkHandlerTester):
    args = ["54321"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService,
                   mock_illust_message_model,
                   FakePostDestination,
                   FakePixivAccountBinder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = FakePostDestination(123456, 56789)
        await context.require(FakePixivAccountBinder).bind(post_dest.adapter, post_dest.user_id, 54321)

        async def except_message():
            illusts = context.require(FakePixivService).spy_random_bookmark.spy_return
            return await IllustMessagesModel.from_illusts(illusts, header="这是您点的私家车")

        await tester(post_dest=post_dest, except_msg=except_message)


class TestRandomBookmarkHandleInvalidArg(RandomBookmarkHandlerTester):
    args = ["5a4b321"]

    @pytest.mark.asyncio
    async def test(self, tester):
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        with pytest.raises(BadRequestError) as e:
            await tester()
        assert e.value.message == "5a4b321不是合法的ID"


class TestRandomBookmarkHandleNoData(RandomBookmarkHandlerTester):
    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService, FakePostDestination, FakePixivAccountBinder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        post_dest = FakePostDestination(123456, 56789)
        await context.require(FakePixivAccountBinder).bind(post_dest.adapter, post_dest.user_id, 54321)

        context.require(FakePixivService).no_data = True

        with pytest.raises(QueryError) as e:
            await tester(post_dest=post_dest)

import pytest

from tests import MyTest
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestRandomBookmarkHandler(FakePixivServiceMixin,
                                FakePixivAccountBinderMixin,
                                MockMessageModelMixin,
                                FakePostDestinationMixin,
                                FakePostmanManagerMixin,
                                MyTest):
    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_account_binder,
                          fake_pixiv_service,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(fake_pixiv_account_binder).bind(post_dest.adapter, post_dest.user_id, 54321)

        await context.require(RandomBookmarkHandler).handle(count=3, post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_random_bookmark.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header="这是您点的私家车")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_not_bind(self, fake_post_destination,
                                   fake_pixiv_account_binder,
                                   fake_pixiv_service,
                                   fake_postman_manager,
                                   mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "无效的Pixiv账号，或未绑定Pixiv账号"

        await context.require(RandomBookmarkHandler).handle(count=3, post_dest=post_dest)

        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_arg(self, fake_post_destination,
                              fake_pixiv_account_binder,
                              fake_pixiv_service,
                              fake_postman_manager,
                              mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(RandomBookmarkHandler).handle("54321", count=3, post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_random_bookmark.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header="这是您点的私家车")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_invalid_arg(self, fake_post_destination,
                                      fake_pixiv_account_binder,
                                      fake_pixiv_service,
                                      fake_postman_manager,
                                      mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "5a4b321不是合法的ID"

        await context.require(RandomBookmarkHandler).handle("5a4b321", count=3, post_dest=post_dest)

        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_no_data(self, fake_post_destination,
                                  fake_pixiv_service,
                                  fake_postman_manager,
                                  mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomBookmarkHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "总之是Pixiv返回的错误信息"

        context.require(fake_pixiv_service).no_data = True

        await context.require(RandomBookmarkHandler).handle("54321", post_dest=post_dest)

        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

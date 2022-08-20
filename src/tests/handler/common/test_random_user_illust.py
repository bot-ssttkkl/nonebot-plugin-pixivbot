import pytest

from tests import MyTest
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestRandomUserIllustHandler(FakePixivServiceMixin,
                                  MockMessageModelMixin,
                                  FakePostDestinationMixin,
                                  FakePostmanManagerMixin,
                                  MyTest):
    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomUserIllustHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(RandomUserIllustHandler).handle("54321", count=3, post_dest=post_dest)

        user, illusts = context.require(fake_pixiv_service).spy_random_user_illust.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header=f"这是您点的{user.name}({user.id})老师的图")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_by_name(self, fake_post_destination,
                                  fake_pixiv_service,
                                  fake_postman_manager,
                                  mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomUserIllustHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(RandomUserIllustHandler).handle("TestUser", count=3, post_dest=post_dest)

        user, illusts = context.require(fake_pixiv_service).spy_random_user_illust.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header=f"这是您点的{user.name}({user.id})老师的图")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_no_data(self, fake_post_destination,
                                  fake_pixiv_service,
                                  fake_postman_manager,
                                  mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomUserIllustHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "总之是Pixiv返回的错误信息"

        context.require(fake_pixiv_service).no_data = True

        await context.require(RandomUserIllustHandler).handle("TestUser", post_dest=post_dest)

        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

import pytest

from tests import MyTest
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestRandomIllustHandler(FakePixivServiceMixin,
                              MockMessageModelMixin,
                              FakePostDestinationMixin,
                              FakePostmanManagerMixin,
                              MyTest):
    @pytest.fixture(autouse=True)
    def remove_interceptor(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomIllustHandler

        context.require(RandomIllustHandler).interceptor = None

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomIllustHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(RandomIllustHandler).handle("some_word", count=3, post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_random_illust.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header="这是您点的some_word图")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_no_data(self, fake_post_destination,
                                  fake_pixiv_service,
                                  fake_postman_manager,
                                  mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomIllustHandler
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "总之是Pixiv返回的错误信息"

        context.require(fake_pixiv_service).no_data = True

        with pytest.raises(QueryError) as e:
            await context.require(RandomIllustHandler).handle("some_word", post_dest=post_dest)
        assert e.value.message == except_msg
import pytest

from tests import MyTest
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestIllustHandler(FakePixivServiceMixin,
                        MockMessageModelMixin,
                        FakePostDestinationMixin,
                        FakePostmanManagerMixin,
                        MyTest):
    @pytest.fixture(autouse=True)
    def remove_interceptor(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import IllustHandler

        context.require(IllustHandler).interceptor = None

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import IllustHandler

        post_dest = fake_post_destination(123456, 56789)

        await context.require(IllustHandler).handle("123456", post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_illust_detail.spy_return
        except_model = await mock_illust_message_model(illusts)

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_no_data(self, fake_post_destination,
                                  fake_pixiv_service,
                                  fake_postman_manager,
                                  mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import IllustHandler
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        post_dest = fake_post_destination(123456, 56789)

        context.require(fake_pixiv_service).no_data = True

        with pytest.raises(QueryError):
            await context.require(IllustHandler).handle("123456", post_dest=post_dest)

    @pytest.mark.asyncio
    async def test_handle_invalid_arg(self, fake_post_destination,
                                      fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import IllustHandler
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "abcdef不是合法的插画ID"

        with pytest.raises(BadRequestError) as e:
            await context.require(IllustHandler).handle("abcdef", post_dest=post_dest)
        assert e.value.message == except_msg

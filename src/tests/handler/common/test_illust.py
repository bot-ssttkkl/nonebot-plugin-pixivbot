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
    async def test_invalid_arg(self, fake_post_destination,
                               fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import IllustHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "abcdef不是合法的插画ID"

        await context.require(IllustHandler).handle("abcdef", post_dest=post_dest)

        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

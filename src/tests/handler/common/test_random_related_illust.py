import pytest

from tests import MyTest
from tests.handler.common.fake_recorder import FakeRecorderMixin
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestRandomRelatedIllustHandler(FakePixivServiceMixin,
                                     FakeRecorderMixin,
                                     MockMessageModelMixin,
                                     FakePostDestinationMixin,
                                     FakePostmanManagerMixin,
                                     MyTest):

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_recorder,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomRelatedIllustHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        context.require(fake_recorder).record_resp(114514, post_dest.identifier)

        await context.require(RandomRelatedIllustHandler).handle(count=3, post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_random_related_illust.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header="这是您点的[114514]的相关图片")

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_no_record_handle(self, fake_post_destination,
                                    fake_pixiv_service,
                                    fake_recorder,
                                    fake_postman_manager,
                                    mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RandomRelatedIllustHandler

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "你还没有发送过请求"

        await context.require(RandomRelatedIllustHandler).handle(count=3, post_dest=post_dest)

        context.require(fake_pixiv_service).random_related_illust.assert_not_awaited()
        context.require(fake_postman_manager).assert_call(post_dest, except_msg)

from unittest.mock import AsyncMock

import pytest

from tests import MyTest
from tests.handler.common.fake_recorder import FakeRecorderMixin
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestMoreHandler(FakePixivServiceMixin,
                      FakeRecorderMixin,
                      MockMessageModelMixin,
                      FakePostDestinationMixin,
                      FakePostmanManagerMixin,
                      MyTest):
    @pytest.fixture(autouse=True)
    def remove_interceptor(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import MoreHandler

        context.require(MoreHandler).interceptor = None

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_recorder,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import MoreHandler
        from nonebot_plugin_pixivbot.handler.common.recorder import Req

        post_dest = fake_post_destination(123456, 56789)
        stub = AsyncMock()

        context.require(fake_recorder).record_req(Req(stub, 114, 514), post_dest.identifier)

        await context.require(MoreHandler).handle(count=3, post_dest=post_dest)

        stub.assert_awaited_once_with(114, 514, count=3, post_dest=post_dest, silently=False)

    @pytest.mark.asyncio
    async def test_no_record_handle(self, fake_post_destination,
                                    fake_pixiv_service,
                                    fake_recorder,
                                    fake_postman_manager,
                                    mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import MoreHandler
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "你还没有发送过请求"

        with pytest.raises(BadRequestError) as e:
            await context.require(MoreHandler).handle(count=3, post_dest=post_dest)
        assert e.value.message == except_msg

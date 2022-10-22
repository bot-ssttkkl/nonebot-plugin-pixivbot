import pytest

from tests import MyTest
from tests.model.mock_message import MockMessageModelMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin


class TestRankingHandler(FakePixivServiceMixin,
                         MockMessageModelMixin,
                         FakePostDestinationMixin,
                         FakePostmanManagerMixin,
                         MyTest):
    @pytest.fixture(autouse=True)
    def remove_interceptor(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RankingHandler

        context.require(RankingHandler).interceptor = None

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_pixiv_service,
                          fake_postman_manager,
                          mock_illust_message_model):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RankingHandler
        from nonebot_plugin_pixivbot.model.message import IllustMessagesModel

        post_dest = fake_post_destination(123456, 56789)

        await context.require(RankingHandler).handle("day", "1-3", post_dest=post_dest)

        illusts = context.require(fake_pixiv_service).spy_illust_ranking.spy_return
        except_model = await IllustMessagesModel.from_illusts(illusts, header="这是您点的日榜", number=1)

        context.require(fake_postman_manager).assert_call(post_dest, except_model)

    @pytest.mark.asyncio
    async def test_handle_invalid_arg_1(self, fake_post_destination,
                                      fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RankingHandler
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "abcdef不是合法的榜单类型"

        with pytest.raises(BadRequestError) as e:
            await context.require(RankingHandler).handle("abcdef", post_dest=post_dest)
        assert e.value.message == except_msg

    @pytest.mark.asyncio
    async def test_handle_invalid_arg_2(self, fake_post_destination,
                                        fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common import RankingHandler
        from nonebot_plugin_pixivbot.utils.errors import BadRequestError

        post_dest = fake_post_destination(123456, 56789)
        except_msg = "abcdef不是合法的范围"

        with pytest.raises(BadRequestError) as e:
            await context.require(RankingHandler).handle("day", "abcdef", post_dest=post_dest)
        assert e.value.message == except_msg

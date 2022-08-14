import pytest

from tests import MyTest
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin


class TestBindHandler(FakePostDestinationMixin,
                      FakePostmanManagerMixin,
                      FakePixivAccountBinderMixin,
                      MyTest):

    @pytest.mark.asyncio
    async def test_handle_no_arg(self, fake_post_destination, fake_postman_manager, fake_pixiv_account_binder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import BindHandler

        bind_handler = context.require(BindHandler)
        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前未绑定Pixiv账号\n命令格式：/pixivbot bind <pixiv_user_id>"

        await bind_handler.handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_bind(self, fake_post_destination, fake_postman_manager, fake_pixiv_account_binder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import BindHandler
        from nonebot_plugin_pixivbot.model import PixivBinding

        bind_handler = context.require(BindHandler)
        post_dest = fake_post_destination(1234, 56789)
        except_msg = "Pixiv账号绑定成功"

        await bind_handler.handle(123321, post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert context.require(fake_pixiv_account_binder).bindings[("test", 1234)] == PixivBinding(adapter="test",
                                                                                                   user_id=1234,
                                                                                                   pixiv_user_id=123321)

    @pytest.mark.asyncio
    async def test_handle_invalid_arg(self, fake_post_destination, fake_postman_manager, fake_pixiv_account_binder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import BindHandler

        bind_handler = context.require(BindHandler)
        post_dest = fake_post_destination(1234, 56789)
        except_msg = "请输入正确格式的Pixiv账号"

        await bind_handler.handle("invalid_arg_lol", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert ("test", 1234) not in context.require(fake_pixiv_account_binder).bindings


class TestUnbindHandler(FakePostDestinationMixin,
                        FakePostmanManagerMixin,
                        FakePixivAccountBinderMixin,
                        MyTest):

    @pytest.mark.asyncio
    async def test_handle_bind(self, fake_post_destination, fake_postman_manager, fake_pixiv_account_binder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import UnbindHandler
        from nonebot_plugin_pixivbot.model import PixivBinding

        context.require(fake_pixiv_account_binder).bindings[("test", 1234)] = PixivBinding(adapter="test",
                                                                                           user_id=1234,
                                                                                           pixiv_user_id=123321)

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "Pixiv账号解绑成功"

        await context.require(UnbindHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert ("test", 1234) not in context.require(fake_pixiv_account_binder).bindings

    @pytest.mark.asyncio
    async def test_handle_not_bind(self, fake_post_destination, fake_postman_manager, fake_pixiv_account_binder):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import UnbindHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前未绑定Pixiv账号"

        await context.require(UnbindHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
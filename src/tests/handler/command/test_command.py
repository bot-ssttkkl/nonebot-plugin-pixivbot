from typing import Sequence

import pytest

from tests import MyTest
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin


class TestCommandHandler(FakePostDestinationMixin,
                         FakePostmanManagerMixin,
                         MyTest):

    @pytest.fixture
    def stub_handler(self, load_pixivbot, fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.handler.command.command import SubCommandHandler, CommandHandler

        @context.require(CommandHandler).sub_command("stub")
        class StubHandler(SubCommandHandler):
            @classmethod
            def type(cls) -> str:
                return "stub"

            def enabled(self) -> bool:
                return True

            def parse_args(self, args: Sequence[str], post_dest: PostDestination[int, int]) -> dict:
                return {"a": args[0], "b": args[1]}

            # noinspection PyMethodOverriding
            async def actual_handle(self, *,
                                    a: str,
                                    b: str,
                                    post_dest: PostDestination[int, int],
                                    silently: bool = False,
                                    **kwargs):
                await self.post_plain_text(f"stub a={a} b={b}", post_dest)

        return StubHandler

    @pytest.mark.asyncio
    async def test_no_arg(self, fake_post_destination,
                          fake_postman_manager,
                          mocker):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import CommandHandler, HelpHandler

        post_dest = fake_post_destination(123456, 56789)
        help_handler = context.require(HelpHandler)
        cmd_handler = context.require(CommandHandler)

        spy = mocker.spy(help_handler, "handle")

        await cmd_handler.handle([], post_dest=post_dest)
        spy.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_subcommand(self, fake_post_destination,
                                      fake_postman_manager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import CommandHandler

        post_dest = fake_post_destination(123456, 56789)
        cmd_handler = context.require(CommandHandler)

        await cmd_handler.handle(["this_should_be_an_invalid_cmd"], post_dest=post_dest)
        assert (post_dest, f"不存在命令 'this_should_be_an_invalid_cmd'") in context.require(fake_postman_manager).calls

    @pytest.mark.asyncio
    async def test(self, fake_post_destination, fake_postman_manager, stub_handler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command import CommandHandler

        post_dest = fake_post_destination(123456, 56789)
        cmd_handler = context.require(CommandHandler)

        await cmd_handler.handle(["stub", "aa", "bb"], post_dest=post_dest)
        assert (post_dest, f"stub a=aa b=bb") in context.require(fake_postman_manager).calls

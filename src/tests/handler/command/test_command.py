from typing import Sequence

import pytest

from tests.handler.common import HandlerTester


class CommandHandlerTester(HandlerTester):
    @pytest.fixture
    def stub_help_handler(self, load_pixivbot, FakePostmanManager):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.handler.command.command import SubCommandHandler, CommandHandler

        @context.require(CommandHandler).sub_command("help")
        class StubHelpHandler(SubCommandHandler):
            @classmethod
            def type(cls) -> str:
                return "help"

            def enabled(self) -> bool:
                return True

            # noinspection PyMethodOverriding
            async def actual_handle(self, *,
                                    post_dest: PostDestination[int, int],
                                    silently: bool = False,
                                    **kwargs):
                await self.post_plain_text(f"stub help", post_dest)

        return StubHelpHandler

    @pytest.fixture
    def stub_handler(self, load_pixivbot, FakePostmanManager):
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

    @pytest.fixture
    def Handler(self, load_pixivbot, stub_help_handler, stub_handler):
        from nonebot_plugin_pixivbot.handler.command.command import CommandHandler
        return CommandHandler


class TestCommandHandlerNoArg(CommandHandlerTester):
    except_msg = "stub help"


class TestCommandHandlerInvalidSubcommand(CommandHandlerTester):
    args = ["this_should_be_an_invalid_cmd"]
    except_msg = "不存在命令 'this_should_be_an_invalid_cmd'"


class TestCommandHandlerStubSubcommand(CommandHandlerTester):
    args = ["stub", "aa", "bb"]
    except_msg = "stub a=aa b=bb"

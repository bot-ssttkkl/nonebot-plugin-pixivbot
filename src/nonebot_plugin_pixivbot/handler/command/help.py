from argparse import Namespace
from typing import Union

from nonebot.exception import ParserExit

from .command import SubCommandHandler
from ...plugin_service import help_service
from ...usage import usage


class HelpHandler(SubCommandHandler, subcommand='help', service=help_service):
    @classmethod
    def type(cls) -> str:
        return "help"

    async def actual_handle(self, *, args: Union[Namespace, ParserExit]):
        await self.post_plain_text(usage)

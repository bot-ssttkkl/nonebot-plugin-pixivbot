from nonebot_plugin_pixivbot.plugin_service import help_service
from .subcommand import SubCommandHandler
from ...usage import usage


class HelpHandler(SubCommandHandler, subcommand='help', service=help_service):
    @classmethod
    def type(cls) -> str:
        return "help"

    async def actual_handle(self):
        await self.post_plain_text(usage)

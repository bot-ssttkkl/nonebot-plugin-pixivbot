from typing import Type, Sequence, Dict, TYPE_CHECKING

from nonebot import logger
from nonebot import on_command
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot_plugin_session import extract_session

from ..base import EntryHandler
from ..utils import get_command_rule

if TYPE_CHECKING:
    from .subcommand import SubCommandHandler


class CommandHandler(EntryHandler):
    subcommand_handlers: Dict[str, Type["SubCommandHandler"]] = dict()

    @classmethod
    def type(cls) -> str:
        return "command"

    @classmethod
    def enabled(cls) -> bool:
        return True

    @classmethod
    def register(cls, subcommand: str, type: Type["SubCommandHandler"]):
        cls.subcommand_handlers[subcommand] = type
        logger.trace(f"registered subcommand {subcommand} for {type}")

    async def parse_args(self, args: Sequence[str]) -> dict:
        return {"args": args}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Sequence[str]):
        logger.debug("args: " + " ".join(map(str, args)))
        if len(args) == 0:
            handler_type = self.subcommand_handlers["help"]
        elif args[0] not in self.subcommand_handlers:
            if not self.silently:
                await self.post_plain_text(f"不存在命令 '{args[0]}'")
            return
        else:
            handler_type = self.subcommand_handlers[args[0]]

        handler = handler_type(self.session, self.event, silently=self.silently,
                               disable_interceptors=self.disable_interceptors)
        await handler.handle(*args[1:])


@on_command("pixivbot", rule=get_command_rule(), priority=5).handle()
async def _(event: Event,
            session=Depends(extract_session)):
    raw_args = str(event.get_message()).strip() + ' '  # 末尾加一个空格用于处理边界

    args = []
    slash = False
    pending_arg = ""
    for c in raw_args:
        if slash:
            pending_arg += c
            slash = False
        elif c == '\\':
            slash = True
        elif c == ' ':
            pending_arg = pending_arg.strip()
            if len(pending_arg) != 0:
                args.append(pending_arg)
                pending_arg = ""
        else:
            pending_arg += c

    logger.debug(f"command args: {args}")
    args = args[1:]

    await CommandHandler(session, event).handle(*args)

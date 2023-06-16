import inspect
from abc import ABC
from argparse import Namespace
from typing import Type, Sequence, Dict, Callable, Optional, Union

from nonebot import logger, on_shell_command
from nonebot.exception import ParserExit
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.rule import ArgumentParser
from nonebot.typing import T_State
from nonebot_plugin_session import extract_session

from ..base import EntryHandler
from ..base import Handler, HandlerMeta
from ..utils import get_command_rule
from ...utils.errors import BadRequestError


class SubCommandHandlerMeta(HandlerMeta):
    def __new__(mcs, *args, **kwargs):
        subcommand = None
        if 'subcommand' in kwargs:
            subcommand = kwargs['subcommand']
            del kwargs['subcommand']

        use_subcommand_parser = None
        if 'use_subcommand_parser' in kwargs:
            use_subcommand_parser = kwargs['use_subcommand_parser']
            del kwargs['use_subcommand_parser']

        cls = super().__new__(mcs, *args, **kwargs)

        if not inspect.isabstract(cls):
            if not subcommand:
                subcommand = cls.type()
            CommandHandler.register(subcommand, cls, use_subcommand_parser)

        return cls


class SubCommandHandler(Handler, ABC, metaclass=SubCommandHandlerMeta):
    async def handle(self, *args, **kwargs):
        raise RuntimeError("Please call handle_with_parsed_args() instead! ")

    async def handle_with_parsed_args(self, *, args: Union[Namespace, ParserExit]):
        try:
            await super().handle_with_parsed_args(args=args)
        except BadRequestError as e:
            await self.handle_bad_request(err=e)

    async def handle_bad_request(self, err: BadRequestError):
        if self.interceptor is not None:
            await self.interceptor.intercept(self, self.actual_handle_bad_request, err)
        else:
            await self.actual_handle_bad_request(err)

    async def actual_handle(self, *, args: Union[Namespace, ParserExit]):
        await super().actual_handle(args=args)

    async def actual_handle_bad_request(self, err: BadRequestError):
        if not self.silently:
            await self.post_plain_text(err.message)


class CommandHandler(EntryHandler):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(help="subcommand", dest="subcommand", required=True)

    subcommand_handlers: Dict[str, Type["SubCommandHandler"]] = dict()

    @classmethod
    def type(cls) -> str:
        return "command"

    @classmethod
    def enabled(cls) -> bool:
        return True

    @classmethod
    def register(cls, subcommand: str, type: Type["SubCommandHandler"],
                 use_subcommand_parser: Optional[Callable[[ArgumentParser], None]] = None):
        cls.subcommand_handlers[subcommand] = type

        subcommand_parser = cls.subparsers.add_parser(subcommand, help=subcommand)
        if use_subcommand_parser is not None:
            use_subcommand_parser(subcommand_parser)

        logger.trace(f"registered subcommand {subcommand} for {type}")

    async def parse_args(self, args: Sequence[str]) -> dict:
        raise RuntimeError("Please call handle_with_parsed_args() instead! ")

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, argv: Sequence[str], args: Union[Namespace, ParserExit]):
        if isinstance(args, ParserExit):
            if len(argv) == 0:
                handler = self.subcommand_handlers["help"](self.session, self.event, silently=self.silently,
                                                           disable_interceptors=self.disable_interceptors)
                await handler.handle_with_parsed_args(args=args)
            else:
                subcommand = argv[0]
                if subcommand not in self.subcommand_handlers:
                    raise BadRequestError(f"不存在命令 {subcommand}")
                else:
                    handler_type = self.subcommand_handlers[subcommand]
                    handler = handler_type(self.session, self.event, silently=self.silently,
                                           disable_interceptors=self.disable_interceptors)
                    await handler.handle_bad_request(BadRequestError())
        else:
            handler_type = self.subcommand_handlers[args.subcommand]
            handler = handler_type(self.session, self.event, silently=self.silently,
                                   disable_interceptors=self.disable_interceptors)
            await handler.handle_with_parsed_args(args=args)


@on_shell_command("pixivbot", parser=CommandHandler.parser, rule=get_command_rule(), priority=5).handle()
async def _(event: Event, state: T_State,
            session=Depends(extract_session)):
    args = state["_args"]
    argv = state["_argv"]
    logger.debug(f"command args: {args}")
    await CommandHandler(session, event).handle_with_parsed_args(argv=argv, args=args)

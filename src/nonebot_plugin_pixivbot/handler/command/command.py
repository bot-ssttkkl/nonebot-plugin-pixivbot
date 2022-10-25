from abc import ABC
from abc import abstractmethod
from typing import Type, Callable, Union, Awaitable, TypeVar, Sequence

from nonebot import logger

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from ..entry_handler import EntryHandler
from ..handler import Handler

UID = TypeVar("UID")
GID = TypeVar("GID")


class SubCommandHandler(Handler, ABC):
    @abstractmethod
    def parse_args(self, args: Sequence[str], post_dest: PostDestination[UID, GID]) -> Union[dict, Awaitable[dict]]:
        raise NotImplementedError()

    async def handle(self, *args,
                     post_dest: PostDestination[UID, GID],
                     silently: bool = False,
                     disabled_interceptors: bool = False,
                     **kwargs):
        try:
            await super().handle(*args, post_dest=post_dest, silently=silently,
                                 disabled_interceptors=disabled_interceptors, **kwargs)
        except BadRequestError as e:
            await self.handle_bad_request(err=e, post_dest=post_dest, silently=silently)

    async def handle_bad_request(self, err: BadRequestError, *,
                                 post_dest: PostDestination[UID, GID],
                                 silently: bool = False):
        if self.interceptor is not None:
            await self.interceptor.intercept(self.actual_handle_bad_request, err,
                                             post_dest=post_dest, silently=silently)
        else:
            await self.actual_handle_bad_request(err, post_dest=post_dest, silently=silently)

    async def actual_handle_bad_request(self, err: BadRequestError, *,
                                        post_dest: PostDestination[UID, GID],
                                        silently: bool = False):
        if not silently:
            await self.post_plain_text(err.message, post_dest=post_dest)


@context.register_singleton()
class CommandHandler(EntryHandler):
    def __init__(self):
        super().__init__()
        self.handlers = dict[str, Type[SubCommandHandler]]()

    @classmethod
    def type(cls) -> str:
        return "command"

    def enabled(self) -> bool:
        return True

    def sub_command(self, type: str) \
            -> Callable[[Type[SubCommandHandler]], Type[SubCommandHandler]]:
        def decorator(cls: Type[SubCommandHandler]):
            if cls not in context:
                context.register_singleton()(cls)
            self.handlers[type] = cls
            logger.trace(f"registered subcommand {type}")
            return cls

        return decorator

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[UID, GID]) -> dict:
        return {"args": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Sequence[str],
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        logger.debug("args: " + " ".join(map(str, args)))
        if len(args) == 0:
            handler = context.require(self.handlers["help"])
        elif args[0] not in self.handlers:
            if not silently:
                await self.post_plain_text(f"不存在命令 '{args[0]}'", post_dest=post_dest)
            return
        else:
            handler = context.require(self.handlers[args[0]])

        await handler.handle(*args[1:], post_dest=post_dest)

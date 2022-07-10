from abc import ABC
from abc import abstractmethod
from typing import Type, Callable, Union, Awaitable, TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.handler import Handler
from nonebot_plugin_pixivbot.handler.interceptor.default_error_interceptor import DefaultErrorInterceptor
from nonebot_plugin_pixivbot.postman import PostDestination, PostIdentifier
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class SubCommandHandler(Handler[UID, GID, B, M], ABC, Generic[UID, GID, B, M]):
    @abstractmethod
    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> Union[dict, Awaitable[dict]]:
        raise NotImplementedError()

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID, B, M]):
        self.postman.send_message(e.message, post_dest=post_dest)


@context.register_singleton()
class CommandHandler(Handler[UID, GID, B, M], Generic[UID, GID, B, M]):
    interceptor = context.require(DefaultErrorInterceptor)

    def __init__(self):
        self.handlers = dict[str, Type[SubCommandHandler[UID, GID, B, M]]]()

    @classmethod
    def type(cls) -> str:
        return "command"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def sub_command(self, type: str) \
            -> Callable[[Type[SubCommandHandler[UID, GID, B, M]]], Type[SubCommandHandler[UID, GID, B, M]]]:
        def decorator(cls: Type[SubCommandHandler[UID, GID, B, M]]):
            context.register_singleton()(cls)
            self.handlers[type] = cls
            return cls

        return decorator

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {"args": args[0]}

    async def actual_handle(self, *, args: Sequence[Any],
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        if len(args) == 0:
            handler = context.require(self.handlers["help"])
        else:
            handler = context.require(self.handlers[args[0]])

        try:
            await handler.handle(*args[1:], post_dest=post_dest)
        except BadRequestError as e:
            await handler.handle_bad_request(e, post_dest)

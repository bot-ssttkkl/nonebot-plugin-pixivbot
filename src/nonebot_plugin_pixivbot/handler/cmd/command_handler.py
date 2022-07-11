from abc import ABC
from abc import abstractmethod
from typing import Type, Callable, Union, Awaitable, TypeVar, Generic, Sequence, Any

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.handler import Handler
from nonebot_plugin_pixivbot.handler.interceptor.default_error_interceptor import DefaultErrorInterceptor
from nonebot_plugin_pixivbot.postman import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")


class SubCommandHandler(Handler[UID, GID], ABC, Generic[UID, GID]):
    @abstractmethod
    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> Union[dict, Awaitable[dict]]:
        raise NotImplementedError()

    async def handle_bad_request(self, e: BadRequestError, post_dest: PostDestination[UID, GID]):
        self.postman.send_plain_text(e.message, post_dest=post_dest)


@context.register_singleton()
class CommandHandler(Handler[UID, GID], Generic[UID, GID]):
    interceptor = context.require(DefaultErrorInterceptor)

    def __init__(self):
        self.handlers = dict[str, Type[SubCommandHandler[UID, GID]]]()

    @classmethod
    def type(cls) -> str:
        return "command"

    @classmethod
    def enabled(cls) -> bool:
        return True

    def sub_command(self, type: str) \
            -> Callable[[Type[SubCommandHandler[UID, GID]]], Type[SubCommandHandler[UID, GID]]]:
        def decorator(cls: Type[SubCommandHandler[UID, GID]]):
            context.register_singleton()(cls)
            self.handlers[type] = cls
            return cls

        return decorator

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        return {"args": args[0]}

    async def actual_handle(self, *, args: Sequence[Any],
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        if len(args) == 0:
            handler = context.require(self.handlers["help"])
        else:
            handler = context.require(self.handlers[args[0]])

        try:
            await handler.handle(*args[1:], post_dest=post_dest)
        except BadRequestError as e:
            await handler.handle_bad_request(e, post_dest)

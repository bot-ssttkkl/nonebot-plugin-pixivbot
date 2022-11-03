from abc import ABC
from typing import Type, Callable, Sequence

from lazy import lazy
from nonebot import Bot, on_command
from nonebot import logger
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from ..base import Handler, MatcherEntryHandler, post_destination
from ..utils import get_command_rule


class SubCommandHandler(Handler, ABC):
    async def handle(self, *args,
                     post_dest: PostDestination[T_UID, T_GID],
                     silently: bool = False,
                     disabled_interceptors: bool = False,
                     **kwargs):
        try:
            await super().handle(*args, post_dest=post_dest, silently=silently,
                                 disabled_interceptors=disabled_interceptors, **kwargs)
        except BadRequestError as e:
            await self.handle_bad_request(err=e, post_dest=post_dest, silently=silently)

    async def handle_bad_request(self, err: BadRequestError, *,
                                 post_dest: PostDestination[T_UID, T_GID],
                                 silently: bool = False):
        if self.interceptor is not None:
            await self.interceptor.intercept(self.actual_handle_bad_request, err,
                                             post_dest=post_dest, silently=silently)
        else:
            await self.actual_handle_bad_request(err, post_dest=post_dest, silently=silently)

    async def actual_handle_bad_request(self, err: BadRequestError, *,
                                        post_dest: PostDestination[T_UID, T_GID],
                                        silently: bool = False):
        if not silently:
            await self.post_plain_text(err.message, post_dest=post_dest)


@context.root.register_eager_singleton()
class CommandHandler(MatcherEntryHandler):
    def __init__(self):
        super().__init__()
        self.handlers = dict[str, Type[SubCommandHandler]]()

    @classmethod
    def type(cls) -> str:
        return "command"

    def enabled(self) -> bool:
        return True

    @lazy
    def matcher(self):
        return on_command("pixivbot", rule=get_command_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
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
        await self.handle(*args, post_dest=post_dest)

    def sub_command(self, type: str) \
            -> Callable[[Type[SubCommandHandler]], Type[SubCommandHandler]]:
        def decorator(cls: Type[SubCommandHandler]):
            if cls not in context:
                context.root.register_singleton()(cls)
            self.handlers[type] = cls
            logger.trace(f"registered subcommand {type}")
            return cls

        return decorator

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        return {"args": args}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, args: Sequence[str],
                            post_dest: PostDestination[T_UID, T_GID],
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

import inspect
from abc import ABC

from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .command import CommandHandler
from ..base import Handler, HandlerMeta


class SubCommandHandlerMeta(HandlerMeta):
    def __new__(mcs, *args, **kwargs):
        subcommand = None
        if 'subcommand' in kwargs:
            subcommand = kwargs['subcommand']
            del kwargs['subcommand']

        cls = super().__new__(mcs, *args, **kwargs)

        if not inspect.isabstract(cls):
            if not subcommand:
                subcommand = cls.type()
            CommandHandler.register(subcommand, cls)

        return cls


class SubCommandHandler(Handler, ABC, metaclass=SubCommandHandlerMeta):
    async def handle(self, *args, **kwargs):
        try:
            await super().handle(*args, **kwargs)
        except BadRequestError as e:
            await self.handle_bad_request(err=e)

    async def handle_bad_request(self, err: BadRequestError):
        if self.interceptor is not None:
            await self.interceptor.intercept(self, self.actual_handle_bad_request, err)
        else:
            await self.actual_handle_bad_request(err)

    async def actual_handle_bad_request(self, err: BadRequestError):
        if not self.silently:
            await self.post_plain_text(err.message)

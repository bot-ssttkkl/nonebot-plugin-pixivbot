from abc import ABC
from typing import TypeVar

from nonebot_plugin_pixivbot.global_context import context
from .handler import Handler
from .interceptor.default_error_interceptor import DefaultErrorInterceptor
from .interceptor.permission_interceptor import BlacklistInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


class EntryHandler(Handler, ABC):
    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(DefaultErrorInterceptor))
        self.add_interceptor(context.require(BlacklistInterceptor))

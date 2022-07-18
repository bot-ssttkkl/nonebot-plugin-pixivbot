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
        super().__init__(context.require(DefaultErrorInterceptor))
        self.set_permission_interceptor(context.require(BlacklistInterceptor))

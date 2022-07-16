from abc import ABC
from typing import TypeVar, Generic

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.handler import Handler
from nonebot_plugin_pixivbot.handler.interceptor.default_error_interceptor import DefaultErrorInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.permission_interceptor import BlacklistInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


class EntryHandler(Handler[UID, GID], ABC, Generic[UID, GID]):
    def __init__(self):
        super().__init__(context.require(DefaultErrorInterceptor))
        self.set_permission_interceptor(context.require(BlacklistInterceptor))

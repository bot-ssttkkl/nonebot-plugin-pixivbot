from abc import ABC
from typing import TypeVar, Generic

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.recorder import Req, Recorder
from nonebot_plugin_pixivbot.handler.handler import Handler
from nonebot_plugin_pixivbot.handler.interceptor.combined_interceptor import CombinedInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.cooldown_interceptor import CooldownInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.default_error_interceptor import DefaultErrorInterceptor
from nonebot_plugin_pixivbot.postman import PostIdentifier
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


class CommonHandler(Handler[UID, GID, B, M], ABC, Generic[UID, GID, B, M]):
    service = context.require(PixivService)
    recorder = context.require(Recorder)

    interceptor = CombinedInterceptor.from_iterable(
        [
            context.require(DefaultErrorInterceptor),
            context.require(CooldownInterceptor)
        ]
    )

    def record_req(self, *args,
                   identifier: PostIdentifier[UID, GID],
                   **kwargs):
        self.recorder.record_req(Req(self, *args, **kwargs), identifier)

    def record_resp_illust(self, illust_id: int,
                           identifier: PostIdentifier[UID, GID]):
        self.recorder.record_resp(illust_id, identifier)

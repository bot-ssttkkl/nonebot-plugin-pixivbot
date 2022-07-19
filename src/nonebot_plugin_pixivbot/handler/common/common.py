from abc import ABC
from typing import TypeVar

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from .recorder import Req, Recorder
from ..entry_handler import EntryHandler
from ..interceptor.cooldown_interceptor import CooldownInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


class CommonHandler(EntryHandler, ABC):
    def __init__(self):
        super().__init__()
        self.service = context.require(PixivService)
        self.recorder = context.require(Recorder)

        self.add_interceptor(context.require(CooldownInterceptor))

    def record_req(self, *args,
                   post_dest: PostDestination[UID, GID],
                   **kwargs):
        self.recorder.record_req(Req(self, *args, **kwargs), post_dest.identifier)

    def record_resp_illust(self, illust_id: int,
                           post_dest: PostDestination[UID, GID]):
        self.recorder.record_resp(illust_id, post_dest.identifier)

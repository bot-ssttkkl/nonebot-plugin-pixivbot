from abc import ABC
from typing import TypeVar, Optional, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .recorder import Recorder
from ..entry_handler import EntryHandler
from ..interceptor.cooldown_interceptor import CooldownInterceptor
from ..interceptor.loading_interceptor import LoadingInterceptor
from ..interceptor.timeout_interceptor import TimeoutInterceptor
from ...model import Illust
from ...model.message import IllustMessageModel, IllustMessagesModel
from ...protocol_dep.postman import PostmanManager
from ...service.pixiv_service import PixivService

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


@context.inject
class RecordPostmanManager:
    recorder: Recorder

    def __init__(self, delegation: PostmanManager):
        self.delegation = delegation

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PD):
        await self.delegation.send_illust(model, post_dest=post_dest)
        self.recorder.record_resp(model.id, post_dest.identifier)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PD):
        await self.delegation.send_illusts(model, post_dest=post_dest)
        if len(model.messages) == 1:
            self.recorder.record_resp(model.messages[0].id, post_dest.identifier)

    def __getattr__(self, name: str):
        return getattr(self.delegation, name)


@context.inject
class CommonHandler(EntryHandler, ABC):
    service: PixivService

    def __init__(self):
        super().__init__()
        # noinspection PyTypeChecker
        self.postman_manager = RecordPostmanManager(self.postman_manager)
        self.add_interceptor(context.require(CooldownInterceptor))
        self.add_interceptor(context.require(TimeoutInterceptor))
        self.add_interceptor(context.require(LoadingInterceptor))

    async def post_illust(self, illust: Illust, *,
                          header: Optional[str] = None,
                          number: Optional[int] = None,
                          post_dest: PD):
        model = await IllustMessageModel.from_illust(illust, header=header, number=number)
        if model is not None:
            await self.postman_manager.send_illust(model, post_dest=post_dest)

    async def post_illusts(self, illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None,
                           post_dest: PD):
        model = await IllustMessagesModel.from_illusts(illusts, header=header, number=number)
        if model:
            await self.postman_manager.send_illusts(model, post_dest=post_dest)

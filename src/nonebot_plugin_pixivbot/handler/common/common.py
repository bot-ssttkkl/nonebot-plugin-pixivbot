from abc import ABC
from asyncio import create_task, gather
from typing import TypeVar, Optional, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .recorder import Recorder
from ..entry_handler import EntryHandler
from ..interceptor.cooldown_interceptor import CooldownInterceptor
from ...model import Illust
from ...model.message import IllustMessageModel, IllustMessagesModel
from ...protocol_dep.postman import PostmanManager
from ...service.pixiv_service import PixivService

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class RecordPostmanManager:
    def __init__(self, delegation: PostmanManager):
        self.delegation = delegation
        self.recorder = context.require(Recorder)

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


class CommonHandler(EntryHandler, ABC):
    def __init__(self):
        super().__init__()
        self.postman_manager = RecordPostmanManager(self.postman_manager)
        self.service = context.require(PixivService)

        self.add_interceptor(context.require(CooldownInterceptor))

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
        tasks = [
            create_task(
                IllustMessageModel.from_illust(x, number=number + i if number is not None else None)
            ) for i, x in enumerate(illusts)
        ]
        await gather(*tasks)

        messages = []
        for t in tasks:
            result = await t
            if result:
                messages.append(result)

        model = IllustMessagesModel(header=header, messages=messages)
        await self.postman_manager.send_illusts(model, post_dest=post_dest)

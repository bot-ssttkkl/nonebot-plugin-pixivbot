from typing import TypeVar, Optional, Any

from beanie import Document
from beanie.odm.operators.update.general import Set
from pymongo import IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PixivBinding
from ..source.mongo import MongoDataSource

UID = TypeVar("UID")


class PixivBindingDocument(PixivBinding[Any], Document):
    class Settings:
        name = "pixiv_binding"
        indexes = [
            IndexModel([("adapter", 1), ("user_id", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(PixivBindingDocument)


@context.register_singleton()
class MongoPixivBindingRepo:
    async def get(self, adapter: str, user_id: UID) -> Optional[PixivBinding]:
        result = await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == adapter,
            PixivBindingDocument.user_id == user_id
        )
        return result

    async def update(self, binding: PixivBinding):
        await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == binding.adapter,
            PixivBindingDocument.user_id == binding.user_id
        ).upsert(
            Set({PixivBindingDocument.pixiv_user_id: binding.pixiv_user_id}),
            on_insert=PixivBindingDocument(**binding.dict())
        )

    async def remove(self, adapter: str, user_id: UID) -> bool:
        cnt = await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == adapter,
            PixivBindingDocument.user_id == user_id
        ).delete()
        return cnt == 1


__all__ = ("MongoPixivBindingRepo",)

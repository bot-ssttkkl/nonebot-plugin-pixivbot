from typing import Optional, Any

from beanie import Document
from beanie.odm.operators.update.general import Set
from pymongo import IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PixivBinding, T_UID
from ..source.mongo import MongoDataSource
from ...context import Inject


class PixivBindingDocument(PixivBinding[Any], Document):
    class Settings:
        name = "pixiv_binding"
        indexes = [
            IndexModel([("adapter", 1), ("user_id", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(PixivBindingDocument)


@context.inject
@context.register_singleton()
class MongoPixivBindingRepo:
    mongo: MongoDataSource = Inject(MongoDataSource)

    async def get(self, adapter: str, user_id: T_UID) -> Optional[PixivBinding]:
        result = await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == adapter,
            PixivBindingDocument.user_id == user_id,
            session=self.mongo.session()
        )
        return result

    async def update(self, binding: PixivBinding):
        session = self.mongo.session()

        await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == binding.adapter,
            PixivBindingDocument.user_id == binding.user_id,
            session=session
        ).upsert(
            Set({PixivBindingDocument.pixiv_user_id: binding.pixiv_user_id}),
            on_insert=PixivBindingDocument(**binding.dict()),
            session=session
        )

    async def remove(self, adapter: str, user_id: T_UID) -> bool:
        session = self.mongo.session()

        cnt = await PixivBindingDocument.find_one(
            PixivBindingDocument.adapter == adapter,
            PixivBindingDocument.user_id == user_id,
            session=session
        ).delete(session=session)
        return cnt == 1


__all__ = ("MongoPixivBindingRepo",)

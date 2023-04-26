from typing import Optional, Any

from beanie.odm.operators.update.general import Set
from pymongo import IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PixivBinding, T_UID
from .base import PixivBindingRepo
from ..source.mongo import MongoDataSource, MongoDocument


class PixivBindingDocument(PixivBinding[Any], MongoDocument):
    class Settings:
        name = "pixiv_binding"
        indexes = [
            IndexModel([("adapter", 1), ("user_id", 1)], unique=True)
        ]


data_source = context.require(MongoDataSource)


@context.register_singleton()
class MongoPixivBindingRepo(PixivBindingRepo):

    async def get(self, adapter: str, user_id: T_UID) -> Optional[PixivBinding]:
        async with data_source.start_session() as session:
            result = await PixivBindingDocument.find_one(
                PixivBindingDocument.adapter == adapter,
                PixivBindingDocument.user_id == user_id,
                session=session
            )
            return result

    async def update(self, binding: PixivBinding):
        async with data_source.start_session() as session:
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
        async with data_source.start_session() as session:
            cnt = await PixivBindingDocument.find_one(
                PixivBindingDocument.adapter == adapter,
                PixivBindingDocument.user_id == user_id,
                session=session
            ).delete(session=session)
            return cnt == 1


__all__ = ("MongoPixivBindingRepo",)

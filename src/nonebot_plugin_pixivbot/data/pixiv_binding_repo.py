from typing import TypeVar, Optional

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PixivBinding
from .source import MongoDataSource

UID = TypeVar("UID")


@context.inject
@context.register_singleton()
class PixivBindingRepo:
    mongo: MongoDataSource

    async def get(self, adapter: str, user_id: UID) -> Optional[PixivBinding]:
        doc = await self.mongo.db.pixiv_binding.find_one(
            {"adapter": adapter, "user_id": user_id}
        )
        if doc:
            return PixivBinding.parse_obj(doc)
        else:
            return None

    async def update(self, binding: PixivBinding):
        await self.mongo.db.pixiv_binding.update_one(
            {"adapter": binding.adapter, "user_id": binding.user_id},
            {"$set": {
                "pixiv_user_id": binding.pixiv_user_id
            }},
            upsert=True
        )

    async def remove(self, adapter: str, user_id: UID) -> bool:
        cnt = await self.mongo.db.pixiv_binding.delete_one(
            {"adapter": adapter, "user_id": user_id}
        )
        return cnt == 1


__all__ = ("PixivBindingRepo",)

from typing import TypeVar, Optional, Generic

from nonebot_plugin_pixivbot.data.source.mongo import MongoDataSource
from nonebot_plugin_pixivbot.global_context import context as context

UID = TypeVar("UID")


@context.register_singleton()
class PixivBindingRepo(Generic[UID]):
    mongo = context.require(MongoDataSource)

    async def bind(self, sender_user_id: UID, pixiv_user_id: int):
        await self.mongo.db.pixiv_binding.update_one({"qq_id": sender_user_id},
                                                     {"$set": {
                                                               "pixiv_user_id": pixiv_user_id
                                                           }},
                                                     upsert=True)

    async def unbind(self, sender_user_id: UID) -> bool:
        cnt = await self.mongo.db.pixiv_binding.delete_one({"qq_id": sender_user_id})
        return cnt == 1

    async def get_binding(self, sender_user_id: UID) -> Optional[UID]:
        result = await self.mongo.db.pixiv_binding.find_one({"qq_id": sender_user_id})
        if result is None:
            return None
        else:
            return result["pixiv_user_id"]


__all__ = ("PixivBindingRepo",)

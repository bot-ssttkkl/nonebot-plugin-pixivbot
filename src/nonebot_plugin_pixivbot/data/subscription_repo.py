from typing import TypeVar, Generic, AsyncGenerator

from nonebot_plugin_pixivbot.data.source.mongo import MongoDataSource
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model import Subscription
from nonebot_plugin_pixivbot.postman import PostIdentifier
from pymongo import ReturnDocument

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.register_singleton()
class SubscriptionRepo(Generic[UID, GID]):
    mongo = context.require(MongoDataSource)

    async def get(self, identifier: ID) -> AsyncGenerator[Subscription, None]:
        if identifier.group_id:
            query = {"group_id": identifier.group_id}
        elif identifier.user_id:
            query = {"user_id": identifier.user_id}
        else:
            raise ValueError("at least one of user_id and group_id should be not None")

        async for obj in self.mongo.db.subscription.find(query):
            yield Subscription.parse_obj(obj)

    async def get_all(self) -> AsyncGenerator[Subscription, None]:
        async for obj in self.mongo.db.subscription.find():
            yield Subscription.parse_obj(obj)

    async def update(self, subscription: Subscription) -> Subscription:
        if subscription.group_id:
            query = {"group_id": subscription.group_id, "type": subscription.type}
        elif subscription.user_id:
            query = {"user_id": subscription.user_id, "type": subscription.type}
        else:
            raise ValueError("at least one of user_id and group_id should be not None")

        return await self.mongo.db.subscription.find_one_and_replace(query, subscription.dict(),
                                                                     return_document=ReturnDocument.BEFORE,
                                                                     upsert=True)

    async def delete(self, type: str, identifier: ID):
        if identifier.group_id:
            query = {"group_id": identifier.group_id, "type": type}
        elif identifier.user_id:
            query = {"user_id": identifier.user_id, "type": type}
        else:
            raise ValueError("at least one of user_id and group_id should be not None")

        if type == 'all':
            del query["type"]
            await self.mongo.db.subscription.delete_many(query)
        else:
            await self.mongo.db.subscription.delete_one(query)


__all__ = ("SubscriptionRepo",)

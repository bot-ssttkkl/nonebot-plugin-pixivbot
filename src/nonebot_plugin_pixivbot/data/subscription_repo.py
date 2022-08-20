from typing import TypeVar, AsyncGenerator, Optional

from pymongo import ReturnDocument

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, ScheduleType
from .source import MongoDataSource
from .utils.process_subscriber import process_subscriber

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.inject
@context.register_singleton()
class SubscriptionRepo:
    mongo: MongoDataSource

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[Subscription, None]:
        query = {
            "subscriber": process_subscriber(subscriber).dict()
        }
        async for obj in self.mongo.db.subscription.find(query):
            yield Subscription.parse_obj(obj)

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[Subscription, None]:
        query = {
            "subscriber.adapter": adapter
        }
        async for obj in self.mongo.db.subscription.find(query):
            yield Subscription.parse_obj(obj)

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        subscription.subscriber = process_subscriber(subscription.subscriber)

        query = {
            "type": subscription.type.value,
            "subscriber": subscription.subscriber.dict()
        }

        sub_dict = subscription.dict()
        sub_dict["type"] = subscription.type.value

        old_doc = await self.mongo.db.subscription.find_one_and_replace(query, sub_dict,
                                                                        return_document=ReturnDocument.BEFORE,
                                                                        upsert=True)
        if old_doc:
            return Subscription.parse_obj(old_doc)
        else:
            return None

    async def delete_one(self, subscriber: ID, type: ScheduleType) -> bool:
        query = {
            "type": type.value,
            "subscriber": process_subscriber(subscriber).dict()
        }
        cnt = await self.mongo.db.subscription.delete_one(query)
        return cnt == 1

    async def delete_many_by_subscriber(self, subscriber: ID):
        query = {
            "subscriber": process_subscriber(subscriber)
        }
        await self.mongo.db.subscription.delete_many(query)


__all__ = ("SubscriptionRepo",)

from typing import TypeVar, AsyncGenerator

from pymongo import ReturnDocument

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, ScheduleType
from .source import MongoDataSource

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.inject
@context.register_singleton()
class SubscriptionRepo:
    mongo: MongoDataSource

    @staticmethod
    def process_subscriber(subscriber: ID) -> PostIdentifier[UID, GID]:
        if subscriber.group_id:
            return PostIdentifier(subscriber.adapter, None, subscriber.group_id)
        elif subscriber.user_id:
            return PostIdentifier(subscriber.adapter, subscriber.user_id, None)
        else:
            raise ValueError("at least one of user_id and group_id should be not None")

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[Subscription, None]:
        query = {
            "subscriber": self.process_subscriber(subscriber).dict()
        }
        async for obj in self.mongo.db.subscription.find(query):
            yield Subscription.parse_obj(obj)

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[Subscription, None]:
        query = {
            "subscriber.adapter": adapter
        }
        async for obj in self.mongo.db.subscription.find(query):
            yield Subscription.parse_obj(obj)

    async def update(self, subscription: Subscription) -> Subscription:
        subscription.subscriber = self.process_subscriber(subscription.subscriber)

        query = {
            "type": subscription.type.value,
            "subscriber": subscription.subscriber.dict()
        }

        sub_dict = subscription.dict()
        sub_dict["type"] = subscription.type.value

        return await self.mongo.db.subscription.find_one_and_replace(query, sub_dict,
                                                                     return_document=ReturnDocument.BEFORE,
                                                                     upsert=True)

    async def delete_one(self, subscriber: ID, type: ScheduleType) -> bool:
        query = {
            "type": type.value,
            "subscriber": self.extract_identifier(subscriber)
        }
        cnt = await self.mongo.db.subscription.delete_one(query)
        return cnt == 1

    async def delete_many_by_subscriber(self, subscriber: ID):
        query = {
            "subscriber": self.extract_identifier(subscriber)
        }
        await self.mongo.db.subscription.delete_many(query)


__all__ = ("SubscriptionRepo",)

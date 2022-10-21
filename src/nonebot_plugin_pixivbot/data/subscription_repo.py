from typing import TypeVar, AsyncGenerator, Optional, List, Any

from beanie import Document, BulkWriter
from pymongo import IndexModel, ReturnDocument

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, ScheduleType
from .source import MongoDataSource
from .utils.process_subscriber import process_subscriber

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class SubscriptionDocument(Subscription[Any, Any], Document):
    class Settings:
        name = "subscription"
        indexes = [
            IndexModel([("subscriber.adapter", 1)]),
            IndexModel([("subscriber", 1), ("type", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(SubscriptionDocument)


@context.inject
@context.register_singleton()
class SubscriptionRepo:
    mongo: MongoDataSource

    @classmethod
    async def get_by_subscriber(cls, subscriber: ID) -> AsyncGenerator[Subscription, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber == subscriber):
            yield doc

    @classmethod
    async def get_by_adapter(cls, adapter: str) -> AsyncGenerator[Subscription, None]:
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber.adapter == adapter):
            yield doc

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        # beanie不支持原子性的find_one_and_replace操作
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

    async def delete_one(self, subscriber: ID, type: ScheduleType) -> Optional[Subscription]:
        # beanie不支持原子性的find_one_and_delete操作
        query = {
            "type": type.value,
            "subscriber": process_subscriber(subscriber).dict()
        }
        result = await self.mongo.db.subscription.find_one_and_delete(query)
        if result:
            return Subscription.parse_obj(result)
        else:
            return None

    @classmethod
    async def delete_many_by_subscriber(cls, subscriber: ID) -> List[Subscription]:
        subscriber = process_subscriber(subscriber)

        old_doc = await SubscriptionDocument.find(
            SubscriptionDocument.subscriber == subscriber
        ).to_list()

        async with BulkWriter() as bw:
            for x in old_doc:
                await x.delete(bulk_writer=bw)

        return old_doc


__all__ = ("SubscriptionRepo",)

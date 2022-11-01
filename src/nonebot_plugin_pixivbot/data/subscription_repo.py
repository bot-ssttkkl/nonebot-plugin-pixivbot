from typing import TypeVar, AsyncGenerator, Optional, List, Any

from beanie import Document, BulkWriter
from pymongo import IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier
from .source import MongoDataSource
from .source.mongo.seq import SeqRepo
from .utils.process_subscriber import process_subscriber
from ..context import Inject

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class SubscriptionDocument(Subscription[Any, Any], Document):
    class Settings:
        name = "subscription"
        indexes = [
            IndexModel([("subscriber.adapter", 1)]),
            IndexModel([("subscriber", 1), ("code", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(SubscriptionDocument)


@context.inject
@context.register_singleton()
class SubscriptionRepo:
    mongo: MongoDataSource = Inject(MongoDataSource)
    seq_repo: SeqRepo = Inject(SeqRepo)

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[Subscription, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber == subscriber):
            yield doc

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[Subscription, None]:
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber.adapter == adapter):
            yield doc

    async def get_by_code(self, subscriber: ID, code: int) -> Optional[Subscription]:
        subscriber = process_subscriber(subscriber)
        return await SubscriptionDocument.find_one(SubscriptionDocument.subscriber == subscriber,
                                                   SubscriptionDocument.code == code)

    async def insert(self, subscription: Subscription):
        subscription.subscriber = process_subscriber(subscription.subscriber)
        subscription.code = await self.seq_repo.inc_and_get(subscription.subscriber.dict())
        await SubscriptionDocument.insert_one(SubscriptionDocument(**subscription.dict()))

    async def delete_one(self, subscriber: ID, code: int) -> Optional[Subscription]:
        subscriber = process_subscriber(subscriber)
        # beanie不支持原子性的find_one_and_delete操作
        query = {
            "code": code,
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

from typing import Optional, Any, AsyncGenerator, Collection

from beanie import Document
from pymongo import IndexModel, DeleteOne

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, T_UID, T_GID
from ..source.mongo import MongoDataSource
from ..utils.process_subscriber import process_subscriber
from ..utils.shortuuid import gen_code


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
class MongoSubscriptionRepo:
    mongo: MongoDataSource = Inject(MongoDataSource)

    async def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncGenerator[Subscription, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber == subscriber,
                                                   session=self.mongo.session()):
            yield doc

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[Subscription, None]:
        async for doc in SubscriptionDocument.find(SubscriptionDocument.subscriber.adapter == adapter,
                                                   session=self.mongo.session()):
            yield doc

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[Subscription]:
        subscriber = process_subscriber(subscriber)
        return await SubscriptionDocument.find_one(SubscriptionDocument.subscriber == subscriber,
                                                   SubscriptionDocument.code == code,
                                                   session=self.mongo.session())

    async def insert(self, subscription: Subscription):
        subscription.subscriber = process_subscriber(subscription.subscriber)
        subscription.code = gen_code()
        await SubscriptionDocument.insert_one(SubscriptionDocument(**subscription.dict()), session=self.mongo.session())

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[Subscription]:
        # beanie不支持原子性的find_one_and_delete操作
        subscriber = process_subscriber(subscriber)
        query = {
            "code": code,
            "subscriber": process_subscriber(subscriber).dict()
        }
        result = await SubscriptionDocument.get_motor_collection().find_one_and_delete(query,
                                                                                       session=self.mongo.session())
        if result:
            return Subscription.parse_obj(result)
        else:
            return None

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[Subscription]:
        session = self.mongo.session()

        subscriber = process_subscriber(subscriber)

        old_doc = await SubscriptionDocument.find(
            SubscriptionDocument.subscriber == subscriber,
            session=session
        ).to_list()

        # BulkWriter存在bug，session不生效

        opt = []
        for x in old_doc:
            opt.append(DeleteOne({"_id": x.id}))

        if len(opt) != 0:
            await SubscriptionDocument.get_motor_collection().bulk_write(opt, ordered=False, session=session)

        return old_doc


__all__ = ("MongoSubscriptionRepo",)

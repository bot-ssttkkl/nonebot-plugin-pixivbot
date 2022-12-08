from typing import Optional, Any, AsyncGenerator, Collection

from beanie import Document
from pymongo import IndexModel, DeleteOne

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Subscription, PostIdentifier, T_UID, T_GID, UserIdentifier
from ..interval_task_repo import process_subscriber
from ..source.mongo import MongoDataSource
from ..utils.shortuuid import gen_code


class SubscriptionDocument(Subscription[Any, Any], Document):
    class Settings:
        name = "subscription"
        indexes = [
            IndexModel([("bot", 1), ("subscriber", 1), ("code", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(SubscriptionDocument)


@context.inject
@context.register_singleton()
class MongoSubscriptionRepo:
    data_source: MongoDataSource = Inject(MongoDataSource)

    async def get_by_subscriber(self, bot: UserIdentifier[T_UID],
                                subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncGenerator[Subscription[T_UID, T_GID], None]:
        subscriber = process_subscriber(subscriber)
        async with self.data_source.start_session() as session:
            async for doc in SubscriptionDocument.find(
                    SubscriptionDocument.bot == bot,
                    SubscriptionDocument.subscriber == subscriber,
                    session=session):
                yield doc

    async def get_by_bot(self, bot: UserIdentifier[T_UID]) -> AsyncGenerator[Subscription[T_UID, T_GID], None]:
        async with self.data_source.start_session() as session:
            async for doc in SubscriptionDocument.find(SubscriptionDocument.bot == bot,
                                                       session=session):
                yield doc

    async def get_by_code(self, bot: UserIdentifier[T_UID],
                          subscriber: PostIdentifier[T_UID, T_GID],
                          code: str) -> Optional[Subscription[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)
        async with self.data_source.start_session() as session:
            return await SubscriptionDocument.find_one(
                SubscriptionDocument.bot == bot,
                SubscriptionDocument.subscriber == subscriber,
                SubscriptionDocument.code == code,
                session=session)

    async def insert(self, item: Subscription[T_UID, T_GID]) -> bool:
        item.subscriber = process_subscriber(item.subscriber)
        item.code = gen_code()
        async with self.data_source.start_session() as session:
            await SubscriptionDocument.insert_one(SubscriptionDocument(**item.dict()), session=session)
        return True

    async def delete_one(self, bot: UserIdentifier[T_UID],
                         subscriber: PostIdentifier[T_UID, T_GID],
                         code: str) -> Optional[Subscription[T_UID, T_GID]]:
        # beanie不支持原子性的find_one_and_delete操作
        subscriber = process_subscriber(subscriber)
        query = {
            "bot": bot.dict(),
            "code": code,
            "subscriber": process_subscriber(subscriber).dict()
        }
        async with self.data_source.start_session() as session:
            result = await SubscriptionDocument.get_motor_collection().find_one_and_delete(query, session=session)
            if result:
                return Subscription.parse_obj(result)
            else:
                return None

    async def delete_many_by_subscriber(self, bot: UserIdentifier[T_UID],
                                        subscriber: PostIdentifier[T_UID, T_GID]) \
            -> Collection[Subscription[T_UID, T_GID]]:
        subscriber = process_subscriber(subscriber)

        async with self.data_source.start_session() as session:
            old_doc = await SubscriptionDocument.find(
                SubscriptionDocument.bot == bot,
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

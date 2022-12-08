from typing import AsyncGenerator, Optional, Any, Collection

from beanie import Document
from pymongo import IndexModel, DeleteOne
from pymongo.errors import DuplicateKeyError

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import WatchTask, PostIdentifier, T_UID, T_GID, UserIdentifier
from ..interval_task_repo import process_subscriber
from ..source.mongo import MongoDataSource
from ..utils.shortuuid import gen_code


class WatchTaskDocument(WatchTask[Any, Any], Document):
    class Settings:
        name = "watch_task"
        indexes = [
            IndexModel([("bot", 1), ("subscriber", 1), ("code", 1)], unique=True),
            IndexModel([("bot", 1), ("subscriber", 1), ("type", 1), ("kwargs", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(WatchTaskDocument)


@context.inject
@context.register_singleton()
class MongoWatchTaskRepo:
    data_source = Inject(MongoDataSource)

    async def get_by_subscriber(self, bot: UserIdentifier[T_UID],
                                subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncGenerator[WatchTask, None]:
        subscriber = process_subscriber(subscriber)
        async with self.data_source.start_session() as session:
            async for doc in WatchTaskDocument.find(
                    WatchTaskDocument.bot == bot,
                    WatchTaskDocument.subscriber == subscriber,
                    session=session):
                yield doc

    async def get_by_bot(self, bot: UserIdentifier[T_UID]) -> AsyncGenerator[WatchTask, None]:
        async with self.data_source.start_session() as session:
            async for doc in WatchTaskDocument.find(WatchTaskDocument.bot == bot,
                                                    session=session):
                yield doc

    async def get_by_code(self, bot: UserIdentifier[T_UID],
                          subscriber: PostIdentifier[T_UID, T_GID],
                          code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)
        async with self.data_source.start_session() as session:
            return await WatchTaskDocument.find_one(
                WatchTaskDocument.bot == bot,
                WatchTaskDocument.subscriber == subscriber,
                WatchTaskDocument.code == code,
                session=session)

    async def insert(self, item: WatchTask) -> bool:
        try:
            async with self.data_source.start_session() as session:
                item.subscriber = process_subscriber(item.subscriber)
                item.code = gen_code()
                doc = WatchTaskDocument(**item.dict())
                await doc.save(session=session)

                return True
        except DuplicateKeyError:
            return False

    async def update(self, item: WatchTask) -> bool:
        async with self.data_source.start_session() as session:
            if isinstance(item, WatchTaskDocument):
                await item.save()
            else:
                item.subscriber = process_subscriber(item.subscriber)
                await WatchTaskDocument.find_one(
                    WatchTaskDocument.subscriber == item.subscriber,
                    WatchTaskDocument.code == item.code,
                    session=session
                ).update(**item.dict(exclude={"subscriber", "code"}),
                         session=session)
            return True

    async def delete_one(self, bot: UserIdentifier[T_UID],
                         subscriber: PostIdentifier[T_UID, T_GID],
                         code: int) -> Optional[WatchTask]:
        async with self.data_source.start_session() as session:
            # beanie不支持原子性的find_one_and_delete操作
            subscriber = process_subscriber(subscriber)
            query = {
                "bot": bot.dict(),
                "code": code,
                "subscriber": process_subscriber(subscriber).dict()
            }
            result = await WatchTaskDocument.get_motor_collection().find_one_and_delete(query, session=session)
            if result:
                return WatchTask.parse_obj(result)
            else:
                return None

    async def delete_many_by_subscriber(self, bot: UserIdentifier[T_UID],
                                        subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[WatchTask]:
        async with self.data_source.start_session() as session:
            subscriber = process_subscriber(subscriber)

            old_doc = await WatchTaskDocument.find(
                WatchTaskDocument.bot == bot,
                WatchTaskDocument.subscriber == subscriber,
                session=session
            ).to_list()

            # BulkWriter存在bug，session不生效

            opt = []
            for x in old_doc:
                opt.append(DeleteOne({"_id": x.id}))

            if len(opt) != 0:
                await WatchTaskDocument.get_motor_collection().bulk_write(opt, ordered=False, session=session)

            return old_doc


__all__ = ("MongoWatchTaskRepo",)

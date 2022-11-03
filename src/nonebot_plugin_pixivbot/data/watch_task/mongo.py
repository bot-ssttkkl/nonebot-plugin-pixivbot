from typing import AsyncGenerator, Optional, Any, Collection

from beanie import Document, BulkWriter
from pymongo import IndexModel
from pymongo.errors import DuplicateKeyError

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import WatchTask, PostIdentifier, T_UID, T_GID
from ..source.mongo import MongoDataSource
from ..utils.process_subscriber import process_subscriber
from ..utils.shortuuid import gen_code


class WatchTaskDocument(WatchTask[Any, Any], Document):
    class Settings:
        name = "watch_task"
        indexes = [
            IndexModel([("subscriber.adapter", 1)]),
            IndexModel([("subscriber", 1), ("code", 1)], unique=True),
            IndexModel([("subscriber", 1), ("type", 1), ("kwargs", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(WatchTaskDocument)


@context.inject
@context.register_singleton()
class MongoWatchTaskRepo:
    mongo = Inject(MongoDataSource)

    async def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncGenerator[WatchTask, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber == subscriber):
            yield doc

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[WatchTask, None]:
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber.adapter == adapter):
            yield doc

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)
        return await WatchTaskDocument.find_one(WatchTaskDocument.subscriber == subscriber,
                                                WatchTaskDocument.code == code)

    async def insert(self, task: WatchTask) -> bool:
        try:
            task.subscriber = process_subscriber(task.subscriber)
            task.code = gen_code()
            doc = WatchTaskDocument(**task.dict())
            await doc.save()

            return True
        except DuplicateKeyError:
            return False

    async def update(self, task: WatchTask) -> bool:
        if isinstance(task, WatchTaskDocument):
            await task.save()
        else:
            task.subscriber = process_subscriber(task.subscriber)
            await WatchTaskDocument.find_one(
                WatchTaskDocument.subscriber == task.subscriber,
                WatchTaskDocument.code == task.code
            ).update(**task.dict(exclude={"subscriber", "code"}))
        return True

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: int) -> Optional[WatchTask]:
        # beanie不支持原子性的find_one_and_delete操作
        subscriber = process_subscriber(subscriber)
        query = {
            "code": code,
            "subscriber": process_subscriber(subscriber).dict()
        }
        result = await self.mongo.db.watch_task.find_one_and_delete(query)
        if result:
            return WatchTask.parse_obj(result)
        else:
            return None

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[WatchTask]:
        subscriber = process_subscriber(subscriber)

        old_doc = await WatchTaskDocument.find(
            WatchTaskDocument.subscriber == subscriber
        ).to_list()

        async with BulkWriter() as bw:
            for x in old_doc:
                await x.delete(bulk_writer=bw)

        return old_doc


__all__ = ("MongoWatchTaskRepo",)
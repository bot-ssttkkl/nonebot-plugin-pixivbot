from typing import TypeVar, AsyncGenerator, Optional, Any, Dict, List

from beanie import Document, BulkWriter
from pymongo import ReturnDocument, IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import WatchTask, WatchType, PostIdentifier
from .source import MongoDataSource
from .utils.process_subscriber import process_subscriber

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class WatchTaskDocument(WatchTask[Any, Any], Document):
    class Settings:
        name = "watch_task"
        indexes = [
            IndexModel([("subscriber.adapter", 1)]),
            IndexModel([("subscriber", 1), ("type", 1), ("kwargs", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(WatchTaskDocument)


@context.inject
@context.register_singleton()
class WatchTaskRepo:
    mongo: MongoDataSource

    @classmethod
    async def get_by_subscriber(cls, subscriber: ID) -> AsyncGenerator[WatchTask, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber == subscriber):
            yield doc

    @classmethod
    async def get_by_adapter(cls, adapter: str) -> AsyncGenerator[WatchTask, None]:
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber.adapter == adapter):
            yield doc

    async def update(self, task: WatchTask) -> Optional[WatchTask]:
        # beanie不支持原子性的find_one_and_replace操作
        task.subscriber = process_subscriber(task.subscriber)

        query = {
            "type": task.type.value,
            "kwargs": task.kwargs,
            "subscriber": task.subscriber.dict(),
        }

        task_dict = task.dict()
        task_dict["type"] = task.type.value

        old_doc = await self.mongo.db.watch_task.find_one_and_replace(query, task_dict,
                                                                      return_document=ReturnDocument.BEFORE,
                                                                      upsert=True)
        if old_doc:
            return WatchTask.parse_obj(old_doc)
        else:
            return None

    async def delete_one(self, type: WatchType,
                         kwargs: Dict[str, Any],
                         subscriber: PostIdentifier[UID, GID]) -> Optional[WatchTask]:
        # beanie不支持原子性的find_one_and_delete操作
        query = {
            "type": type.value,
            "kwargs": kwargs,
            "subscriber": process_subscriber(subscriber).dict(),
        }
        result = await self.mongo.db.watch_task.find_one_and_delete(query)
        if result:
            return WatchTask.parse_obj(result)
        else:
            return None

    @classmethod
    async def delete_many_by_subscriber(cls, subscriber: ID) -> List[WatchTask]:
        subscriber = process_subscriber(subscriber)

        old_doc = await WatchTaskDocument.find(
            WatchTaskDocument.subscriber == subscriber
        ).to_list()

        async with BulkWriter() as bw:
            for x in old_doc:
                await x.delete(bulk_writer=bw)

        return old_doc


__all__ = ("WatchTaskRepo",)

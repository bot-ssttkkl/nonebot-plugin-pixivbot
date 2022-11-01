from typing import TypeVar, AsyncGenerator, Optional, Any, List

from beanie import Document, BulkWriter
from pymongo import IndexModel

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import WatchTask, PostIdentifier
from .source import MongoDataSource
from .source.mongo.seq import SeqRepo
from .utils.process_subscriber import process_subscriber
from ..context import Inject

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


class WatchTaskDocument(WatchTask[Any, Any], Document):
    class Settings:
        name = "watch_task"
        indexes = [
            IndexModel([("subscriber.adapter", 1)]),
            IndexModel([("subscriber", 1), ("code", 1)], unique=True)
        ]


context.require(MongoDataSource).document_models.append(WatchTaskDocument)


@context.inject
@context.register_singleton()
class WatchTaskRepo:
    mongo = Inject(MongoDataSource)
    seq_repo: SeqRepo = Inject(SeqRepo)

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[WatchTask, None]:
        subscriber = process_subscriber(subscriber)
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber == subscriber):
            yield doc

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[WatchTask, None]:
        async for doc in WatchTaskDocument.find(WatchTaskDocument.subscriber.adapter == adapter):
            yield doc

    async def get_by_code(self, subscriber: ID, code: int) -> Optional[WatchTask]:
        subscriber = process_subscriber(subscriber)
        return await WatchTaskDocument.find_one(WatchTaskDocument.subscriber == subscriber,
                                                WatchTaskDocument.code == code)

    async def insert(self, task: WatchTask):
        task.subscriber = process_subscriber(task.subscriber)
        task.code = await self.seq_repo.inc_and_get(task.subscriber.dict() | {"type": "watch_task"})
        await WatchTaskDocument.insert_one(WatchTaskDocument(**task.dict()))

    async def update(self, task: WatchTask):
        if isinstance(task, WatchTaskDocument):
            await task.save()
        else:
            task.subscriber = process_subscriber(task.subscriber)
            await WatchTaskDocument.find_one(
                WatchTaskDocument.subscriber == task.subscriber,
                WatchTaskDocument.code == task.code
            ).update(**task.dict(exclude={"subscriber", "code"}))

    async def delete_one(self, subscriber: ID, code: int) -> Optional[WatchTask]:
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

    async def delete_many_by_subscriber(self, subscriber: ID) -> List[WatchTask]:
        subscriber = process_subscriber(subscriber)

        old_doc = await WatchTaskDocument.find(
            WatchTaskDocument.subscriber == subscriber
        ).to_list()

        async with BulkWriter() as bw:
            for x in old_doc:
                await x.delete(bulk_writer=bw)

        return old_doc


__all__ = ("WatchTaskRepo",)

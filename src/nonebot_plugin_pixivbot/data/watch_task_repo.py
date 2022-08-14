from typing import TypeVar, AsyncGenerator, Dict, Any, Optional

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model.identifier import PostIdentifier
from pymongo import ReturnDocument

from .source import MongoDataSource
from ..enums import WatchType
from ..model.watch_task import WatchTask

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.inject
@context.register_singleton()
class WatchTaskRepo:
    mongo: MongoDataSource

    async def get(self, type: WatchType,
                  args: Dict[str, Any],
                  subscriber: ID):
        query = {
            "type": type.value,
            "args": args,
            "subscriber": subscriber.dict(),
        }
        return WatchTask.parse_obj(
            await self.mongo.db.watch_task.find_one(query)
        )

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[WatchTask, None]:
        query = {
            "subscriber": subscriber.dict(),
        }
        async for obj in self.mongo.db.watch_task.find(query):
            yield WatchTask.parse_obj(obj)

    async def get_by_adapter(self, adapter: str) -> AsyncGenerator[WatchTask, None]:
        query = {
            "subscriber.adapter": adapter
        }
        async for obj in self.mongo.db.watch_task.find(query):
            yield WatchTask.parse_obj(obj)

    async def update(self, task: WatchTask) -> Optional[WatchTask]:
        query = {
            "type": task.type.value,
            "args": task.kwargs,
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
                         args: Dict[str, Any],
                         subscriber: PostIdentifier[UID, GID]):
        query = {
            "type": type.value,
            "args": args,
            "subscriber": subscriber.dict(),
        }
        await self.mongo.db.watch_task.delete_one(query)


__all__ = ("WatchTaskRepo",)

from typing import TypeVar, AsyncGenerator, Optional, Any, Dict

from pymongo import ReturnDocument

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import WatchTask, WatchType, PostIdentifier
from .source import MongoDataSource
from .utils.process_subscriber import process_subscriber

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


@context.inject
@context.register_singleton()
class WatchTaskRepo:
    mongo: MongoDataSource

    # async def get(self, type: WatchType,
    #               args: Dict[str, Any],
    #               subscriber: ID):
    #     query = {
    #         "type": type.value,
    #         "args": args,
    #         "subscriber": subscriber.dict(),
    #     }
    #     return WatchTask.parse_obj(
    #         await self.mongo.db.watch_task.find_one(query)
    #     )

    async def get_by_subscriber(self, subscriber: ID) -> AsyncGenerator[WatchTask, None]:
        query = {
            "subscriber": process_subscriber(subscriber).dict()
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
                         subscriber: PostIdentifier[UID, GID]) -> bool:
        query = {
            "type": type.value,
            "kwargs": kwargs,
            "subscriber": process_subscriber(subscriber).dict(),
        }
        cnt = await self.mongo.db.watch_task.delete_one(query)
        return cnt != 0

    async def delete_many_by_subscriber(self, subscriber: ID):
        query = {
            "subscriber": process_subscriber(subscriber)
        }
        await self.mongo.db.watch_task.delete_many(query)


__all__ = ("WatchTaskRepo",)

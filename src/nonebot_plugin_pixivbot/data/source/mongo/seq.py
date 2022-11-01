from typing import Any

from beanie import Document
from pymongo import IndexModel, ReturnDocument

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source import MongoDataSource


class Seq(Document):
    key: Any
    value: int = 0

    class Settings:
        name = "seq"
        indexes = [
            IndexModel([("key", 1)], unique=True),
        ]


context.require(MongoDataSource).document_models.append(Seq)


@context.inject
@context.register_singleton()
class SeqRepo:
    mongo = Inject(MongoDataSource)

    async def inc_and_get(self, key: Any) -> int:
        seq = await self.mongo.db.seq.find_one_and_update({'key': key},
                                                          {'$inc': {'value': 1}},
                                                          upsert=True,
                                                          return_document=ReturnDocument.AFTER)
        return seq["value"]

    async def get_and_inc(self, key: Any) -> int:
        seq = await self.mongo.db.seq.find_one_and_update({'key': key},
                                                          {'$inc': {'value': 1}},
                                                          upsert=True,
                                                          return_document=ReturnDocument.BEFORE)
        return seq["value"]

    async def get(self, key: Any) -> int:
        seq = await self.mongo.db.seq.find_one({'key': key})
        value = None
        if seq is not None:
            value = seq.get("value")
        return value if value is not None else 0

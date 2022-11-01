from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from nonebot_plugin_pixivbot import context
from .mongo_migration import MongoMigration
from .mongo_migration_manager import MongoMigrationManager


@context.require(MongoMigrationManager).register
class MongoV4ToV5(MongoMigration):
    from_db_version = 4
    to_db_version = 5

    async def inc_and_get(self, db: AsyncIOMotorDatabase, key: Any) -> int:
        seq = await db.seq.find_one_and_update({'key': key},
                                               {'$inc': {'value': 1}},
                                               upsert=True,
                                               return_document=ReturnDocument.AFTER)
        return seq["value"]

    async def migrate(self, db: AsyncIOMotorDatabase):
        await self.migrate_subscription(db)
        await self.migrate_watch_task(db)

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("subscriber_1_type_1")
        except:
            pass

        async for sub in db["subscription"].find():
            code = await self.inc_and_get(db, sub["subscriber"] | {"type": "subscription"})
            await db["subscription"].update_one(sub, {"$set": {"code": code}})

    async def migrate_watch_task(self, db: AsyncIOMotorDatabase):
        try:
            await db["watch_task"].drop_index("subscriber_1_type_1_kwargs_1")
        except:
            pass

        async for sub in db["watch_task"].find():
            code = await self.inc_and_get(db, sub["subscriber"] | {"type": "watch_task"})
            await db["watch_task"].update_one(sub, {"$set": {"code": code}})

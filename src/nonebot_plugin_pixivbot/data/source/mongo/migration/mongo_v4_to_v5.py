from motor.motor_asyncio import AsyncIOMotorDatabase

from nonebot_plugin_pixivbot import context
from .mongo_migration import MongoMigration
from .mongo_migration_manager import MongoMigrationManager
from ....utils.shortuuid import gen_code


@context.require(MongoMigrationManager).register
class MongoV4ToV5(MongoMigration):
    from_db_version = 4
    to_db_version = 5

    async def migrate(self, db: AsyncIOMotorDatabase):
        await self.migrate_subscription(db)
        await self.migrate_watch_task(db)

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("subscriber_1_type_1")
        except:
            pass

        async for sub in db["subscription"].find():
            code = gen_code()
            await db["subscription"].update_one(sub, {"$set": {"code": code}})

    async def migrate_watch_task(self, db: AsyncIOMotorDatabase):
        try:
            await db["watch_task"].drop_index("subscriber_1_type_1_kwargs_1")
        except:
            pass

        async for sub in db["watch_task"].find():
            code = gen_code()
            await db["watch_task"].update_one(sub, {"$set": {"code": code}})

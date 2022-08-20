from motor.motor_asyncio import AsyncIOMotorDatabase

from nonebot_plugin_pixivbot import context
from .mongo_migration import MongoMigration
from .mongo_migration_manager import MongoMigrationManager


@context.require(MongoMigrationManager).register
class MongoV3ToV4(MongoMigration):
    from_db_version = 3
    to_db_version = 4

    async def migrate(self, db: AsyncIOMotorDatabase):
        await self.migrate_subscription(db)

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("adapter_1_group_id_1_type_1")
        except:
            pass

        try:
            await db["subscription"].drop_index("adapter_1_user_id_1_type_1")
        except:
            pass

        await db["subscription"].update_many(
            {},
            [
                {
                    "$set": {
                        "subscriber": {
                            "adapter": "$$ROOT.adapter",
                            "user_id": "$$ROOT.user_id",
                            "group_id": "$$ROOT.group_id",
                        }
                    }
                },
                {
                    "$unset": [
                        "adapter",
                        "user_id",
                        "group_id"
                    ]
                }
            ]
        )

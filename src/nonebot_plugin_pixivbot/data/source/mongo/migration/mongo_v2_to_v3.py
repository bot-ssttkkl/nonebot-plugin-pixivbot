from motor.motor_asyncio import AsyncIOMotorDatabase

from nonebot_plugin_pixivbot import context
from .mongo_migration import MongoMigration
from .mongo_migration_manager import MongoMigrationManager


@context.require(MongoMigrationManager).register
class MongoV2ToV3(MongoMigration):
    from_db_version = 2
    to_db_version = 3

    async def migrate(self, db: AsyncIOMotorDatabase):
        await db.download_cache.delete_many({})
        await db.illust_detail_cache.delete_many({})
        await db.user_detail_cache.delete_many({})
        await db.illust_ranking_cache.delete_many({})
        await db.search_illust_cache.delete_many({})
        await db.search_user_cache.delete_many({})
        await db.user_illusts_cache.delete_many({})
        await db.user_bookmarks_cache.delete_many({})
        await db.other_cache.delete_many({})

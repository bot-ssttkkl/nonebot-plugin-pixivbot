from motor.motor_asyncio import AsyncIOMotorDatabase

from nonebot_plugin_pixivbot.data.source.migration_manager import Migration, MigrationManager


class MongoMigration(Migration[AsyncIOMotorDatabase]):
    ...


mongo_migration_manager = MigrationManager()

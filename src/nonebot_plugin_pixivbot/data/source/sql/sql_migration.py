from sqlalchemy.ext.asyncio import AsyncConnection

from nonebot_plugin_pixivbot.data.source.migration_manager import Migration, MigrationManager


class SqlMigration(Migration[AsyncConnection]):
    ...


sql_migration_manager = MigrationManager()

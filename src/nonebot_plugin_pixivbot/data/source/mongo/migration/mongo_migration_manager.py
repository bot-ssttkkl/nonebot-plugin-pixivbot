from typing import Type, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from nonebot import logger

from nonebot_plugin_pixivbot.data.source.mongo.migration.mongo_migration import MongoMigration
from nonebot_plugin_pixivbot.global_context import context


@context.register_singleton()
class MongoMigrationManager:
    def __init__(self):
        self._mapping = dict[int, list[MongoMigration]]()

    def add(self, migration: MongoMigration):
        if migration.from_db_version not in self._mapping:
            self._mapping[migration.from_db_version] = []
        self._mapping[migration.from_db_version].append(migration)

    def register(self, migration_cls: Type[MongoMigration]) -> Type[MongoMigration]:
        self.add(migration_cls())
        return migration_cls

    async def perform_migration(self, client: AsyncIOMotorDatabase, from_db_version: int, to_db_version: int):
        while from_db_version < to_db_version:
            from_migrations = self._mapping.get(from_db_version, [])

            choice: Optional[MongoMigration] = None
            for mig in from_migrations:
                if choice is None or (choice.to_db_version < mig.to_db_version <= to_db_version):
                    choice = mig

            if choice is None:
                raise NoMigrationError(from_db_version, to_db_version)

            await choice.migrate(client)
            logger.success(f"migrated from {from_db_version} to {choice.to_db_version}")
            from_db_version = choice.to_db_version


class NoMigrationError(Exception):
    def __init__(self, from_db_version: int, to_db_version: int):
        super().__init__()
        self.from_db_version = from_db_version
        self.to_db_version = to_db_version

    def __str__(self):
        return f"no migration from {self.from_db_version} to {self.to_db_version}"

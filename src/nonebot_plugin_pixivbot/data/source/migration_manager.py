from typing import Type, Optional, Generic, Protocol, TypeVar, Dict, List

from nonebot import logger

T_Conn = TypeVar("T_Conn")


class Migration(Protocol[T_Conn]):
    from_db_version: int
    to_db_version: int

    async def migrate(self, conn: T_Conn):
        ...


T_Migration = TypeVar("T_Migration", bound=Migration)


class MigrationManager(Generic[T_Migration]):
    def __init__(self):
        self._mapping: Dict[int, List[Type[T_Migration]]] = {}

    def add(self, migration: Type[T_Migration]) -> Type[T_Migration]:
        if migration.from_db_version not in self._mapping:
            self._mapping[migration.from_db_version] = []
        self._mapping[migration.from_db_version].append(migration)
        return migration

    async def perform_migration(self, conn: T_Conn, from_db_version: int, to_db_version: int) -> int:
        while from_db_version < to_db_version:
            from_migrations = self._mapping.get(from_db_version, [])

            choice: Optional[Type[T_Migration]] = None
            for mig in from_migrations:
                if choice is None or (choice.to_db_version < mig.to_db_version <= to_db_version):
                    choice = mig

            if choice is None:
                raise NoMigrationError(from_db_version, to_db_version)

            if getattr(choice, "deferred", False):
                if to_db_version != choice.to_db_version:
                    raise RuntimeError("only the last migration can be deferred")
                await choice().migrate(conn)
                logger.success(f"migrated from {from_db_version} to {choice.to_db_version}  (deferred)")
                return from_db_version
            else:
                await choice().migrate(conn)
                logger.success(f"migrated from {from_db_version} to {choice.to_db_version}")
                from_db_version = choice.to_db_version

        return to_db_version


class NoMigrationError(Exception):
    def __init__(self, from_db_version: int, to_db_version: int):
        super().__init__()
        self.from_db_version = from_db_version
        self.to_db_version = to_db_version

    def __str__(self):
        return f"no migration from {self.from_db_version} to {self.to_db_version}"

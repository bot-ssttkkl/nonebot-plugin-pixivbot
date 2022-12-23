from functools import partial
from typing import Type, Optional, Generic, Protocol, TypeVar, Dict, List, Callable, Awaitable, Union

from nonebot import logger

T_Conn = TypeVar("T_Conn")


class Migration(Protocol[T_Conn]):
    from_db_version: int
    to_db_version: int

    async def migrate(self, conn: T_Conn):
        ...


class DeferrableMigration(Protocol[T_Conn]):
    deferred = True

    from_db_version: int
    to_db_version: int
    safe: bool

    async def migrate(self, conn: T_Conn, on_migrated: Callable[[], Awaitable[None]]):
        ...


T_Migration = TypeVar("T_Migration", bound=Union[Migration, DeferrableMigration])


class MigrationManager(Generic[T_Migration]):
    def __init__(self, on_migrated: Callable[[int, int], Awaitable[None]]):
        self._mapping: Dict[int, List[Type[T_Migration]]] = {}
        self._on_migrated = on_migrated

    def add(self, migration: Type[T_Migration]) -> Type[T_Migration]:
        if migration.from_db_version not in self._mapping:
            self._mapping[migration.from_db_version] = []
        self._mapping[migration.from_db_version].append(migration)
        return migration

    async def perform_migration(self, conn: T_Conn, from_db_version: int, to_db_version: int):
        current_db_version = from_db_version

        while current_db_version < to_db_version:
            from_migrations = self._mapping.get(current_db_version, [])

            choice: Optional[Type[T_Migration]] = None
            for mig in from_migrations:
                if choice is None or (choice.to_db_version < mig.to_db_version <= to_db_version):
                    choice = mig

            if choice is None:
                raise NoMigrationError(current_db_version, to_db_version)

            if getattr(choice, "deferred", False):
                if not choice.safe and to_db_version != choice.to_db_version:
                    raise RuntimeError("only the last migration can be deferred")

                async def on_migrated(migration):
                    nonlocal to_db_version
                    if to_db_version == migration.to_db_version:
                        await self._on_migrated(migration.from_db_version, to_db_version)
                    logger.success(f"migrated from {migration.from_db_version} to {migration.to_db_version} (deferred)")

                await choice().migrate(conn, partial(on_migrated, choice))
                logger.success(f"deferred migration from {current_db_version} to {choice.to_db_version}")
            else:
                await choice().migrate(conn)
                await self._on_migrated(current_db_version, to_db_version)
                logger.success(f"migrated from {current_db_version} to {choice.to_db_version}")

            current_db_version = choice.to_db_version


class NoMigrationError(Exception):
    def __init__(self, from_db_version: int, to_db_version: int):
        super().__init__()
        self.from_db_version = from_db_version
        self.to_db_version = to_db_version

    def __str__(self):
        return f"no migration from {self.from_db_version} to {self.to_db_version}"

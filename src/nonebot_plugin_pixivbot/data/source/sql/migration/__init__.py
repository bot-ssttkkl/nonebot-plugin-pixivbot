from typing import Callable, Awaitable

from .sql_v1_to_v2 import SqlV1ToV2
from .sql_v2_to_v3 import SqlV2ToV3
from .sql_v3_to_v4 import SqlV3ToV4
from .sql_v4_to_v5 import SqlV4ToV5
from ...migration_manager import MigrationManager


class SqlMigrationManager(MigrationManager):
    def __init__(self, on_migrated: Callable[[int, int], Awaitable[None]]):
        super().__init__(on_migrated)
        self.add(SqlV1ToV2)
        self.add(SqlV2ToV3)
        self.add(SqlV3ToV4)
        self.add(SqlV4ToV5)

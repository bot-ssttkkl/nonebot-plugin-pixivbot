from sqlalchemy.ext.asyncio import AsyncConnection

from .sql_v1_to_v2 import SqlV1ToV2
from .sql_v2_to_v3 import SqlV2ToV3
from ...migration_manager import Migration, MigrationManager

sql_migration_manager = MigrationManager[Migration[AsyncConnection]]()
sql_migration_manager.add(SqlV1ToV2)
sql_migration_manager.add(SqlV2ToV3)

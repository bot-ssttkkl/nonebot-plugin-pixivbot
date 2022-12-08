from sqlalchemy.ext.asyncio import AsyncConnection

from .sql_v1_to_v2 import SqlV1ToV2
from ...migration_manager import Migration, MigrationManager

sql_migration_manager = MigrationManager[Migration[AsyncConnection]]()
sql_migration_manager.add(SqlV1ToV2)

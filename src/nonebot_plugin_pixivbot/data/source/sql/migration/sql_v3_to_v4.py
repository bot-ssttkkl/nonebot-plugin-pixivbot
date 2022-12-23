from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nonebot_plugin_pixivbot.data.source.migration_manager import Migration


class SqlV3ToV4(Migration):
    from_db_version = 3
    to_db_version = 4

    async def migrate(self, conn: AsyncConnection):
        await conn.execute(text("drop table download_cache;"))

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...migration_manager import Migration


class MongoV6ToV7(Migration):
    from_db_version = 6
    to_db_version = 7

    async def migrate(self, conn: AsyncIOMotorDatabase):
        try:
            await conn["download_cache"].drop_index("illust_id_1")
        except:
            pass

        await conn["download_cache"].delete_many({})

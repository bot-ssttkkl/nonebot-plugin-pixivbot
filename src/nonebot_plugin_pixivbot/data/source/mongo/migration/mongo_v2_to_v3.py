from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoV2ToV3:
    from_db_version = 2
    to_db_version = 3

    async def migrate(self, conn: AsyncIOMotorDatabase):
        await conn.download_cache.delete_many({})
        await conn.illust_detail_cache.delete_many({})
        await conn.user_detail_cache.delete_many({})
        await conn.illust_ranking_cache.delete_many({})
        await conn.search_illust_cache.delete_many({})
        await conn.search_user_cache.delete_many({})
        await conn.user_illusts_cache.delete_many({})
        await conn.user_bookmarks_cache.delete_many({})
        await conn.other_cache.delete_many({})

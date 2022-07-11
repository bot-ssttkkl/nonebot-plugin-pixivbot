from motor.motor_asyncio import AsyncIOMotorClient
from nonebot import logger, get_driver
from pymongo.errors import OperationFailure

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.source.mongo.migration import MongoMigrationManager
from nonebot_plugin_pixivbot.global_context import context as context


@context.register_singleton()
class MongoDataSource:
    conf = context.require(Config)
    app_db_version = 2

    def __init__(self):
        self._client = None
        self._db = None

        get_driver().on_startup(self.initialize)
        get_driver().on_shutdown(self.finalize)

    @property
    def client(self):
        return self._client

    @property
    def db(self):
        return self._db

    async def get_db_version(self) -> int:
        version = await self.db["meta_info"].find_one({"key": "db_version"})
        if version is None:
            await self.db["meta_info"].insert_one({"key": "db_version", "value": 1})
            return 1
        else:
            return version["value"]

    async def set_db_version(self, db_version: int):
        await self.db["meta_info"].update_one({"key": "db_version"},
                                              {"$set": {
                                                  "value": db_version
                                              }},
                                              upsert=True)

    async def _ensure_index(self, coll_name: str, indexes: list[tuple[str, int]], **kwargs):
        try:
            await self.db[coll_name].create_index(indexes, **kwargs)
        except OperationFailure:
            logger.info(f"Index in {coll_name}: recreated")
            await self.db[coll_name].drop_index(indexes)
            await self.db[coll_name].create_index(indexes, **kwargs)

    async def _ensure_ttl_index(self, coll_name: str, expires_in: int):
        try:
            await self.db[coll_name].create_index([("update_time", 1)], expireAfterSeconds=expires_in)
        except OperationFailure:
            await self.db.command({
                "collMod": coll_name,
                "index": {
                    "keyPattern": {"update_time": 1},
                    "expireAfterSeconds": expires_in,
                }
            })
            logger.success(f"TTL Index in {coll_name}: expireAfterSeconds changed to {expires_in}")

    async def initialize(self):
        self._client = AsyncIOMotorClient(self.conf.pixiv_mongo_conn_url)
        self._db = self._client[self.conf.pixiv_mongo_database_name]

        # migrate
        db_version = await self.get_db_version()
        await context.require(MongoMigrationManager).perform_migration(self._db, db_version, self.app_db_version)
        await self.set_db_version(self.app_db_version)

        # ensure index
        await self._ensure_index('meta_info', [("key", 1)], unique=True)

        await self._ensure_index('pixiv_binding', [("adapter", 1), ("user_id", 1)], unique=True)

        await self._ensure_index('subscription', [("adapter", 1), ("user_id", 1), ("type", 1)])
        await self._ensure_index('subscription', [("adapter", 1), ("group_id", 1), ("type", 1)])

        await self._ensure_index('local_tags', [("name", 1)], unique=True)
        await self._ensure_index('local_tags', [("translated_name", 1)])

        await self._ensure_index('download_cache', [("illust_id", 1)], unique=True)
        await self._ensure_ttl_index('download_cache', self.conf.pixiv_download_cache_expires_in)

        await self._ensure_index('illust_detail_cache', [("illust.id", 1)], unique=True)
        await self._ensure_ttl_index('illust_detail_cache', self.conf.pixiv_illust_detail_cache_expires_in)

        await self._ensure_index('user_detail_cache', [("user.id", 1)], unique=True)
        await self._ensure_ttl_index('user_detail_cache', self.conf.pixiv_user_detail_cache_expires_in)

        await self._ensure_index('illust_ranking_cache', [("mode", 1)], unique=True)
        await self._ensure_ttl_index('illust_ranking_cache', self.conf.pixiv_illust_ranking_cache_expires_in)

        await self._ensure_index('search_illust_cache', [("word", 1)], unique=True)
        await self._ensure_ttl_index('search_illust_cache', self.conf.pixiv_search_illust_cache_expires_in)

        await self._ensure_index('search_user_cache', [("word", 1)], unique=True)
        await self._ensure_ttl_index('search_user_cache', self.conf.pixiv_search_user_cache_expires_in)

        await self._ensure_index('user_illusts_cache', [("user_id", 1)], unique=True)
        await self._ensure_ttl_index('user_illusts_cache', self.conf.pixiv_user_illusts_cache_expires_in)

        await self._ensure_index('user_bookmarks_cache', [("user_id", 1)], unique=True)
        await self._ensure_ttl_index('user_bookmarks_cache', self.conf.pixiv_user_bookmarks_cache_expires_in)

        await self._ensure_index('related_illusts_cache', [("original_illust_id", 1)], unique=True)
        await self._ensure_ttl_index('related_illusts_cache', self.conf.pixiv_related_illusts_cache_expires_in)

        await self._ensure_index('other_cache', [("type", 1)], unique=True)
        await self._ensure_ttl_index('other_cache', self.conf.pixiv_other_cache_expires_in)
        logger.success("ensure indexes completed")

    async def finalize(self):
        self._client.close()
        self._client = None
        self._db = None


__all__ = ("MongoDataSource",)

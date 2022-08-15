from bson import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from nonebot import logger
from pymongo.errors import OperationFailure

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.errors import DataSourceNotReadyError
from nonebot_plugin_pixivbot.data.source.mongo.migration import MongoMigrationManager
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.lifecycler import on_shutdown, on_startup


@context.inject
@context.register_eager_singleton()
class MongoDataSource:
    conf: Config
    mongo_migration_mgr: MongoMigrationManager
    app_db_version = 4

    def __init__(self):
        self._client = None
        self._db = None

        on_startup(self.initialize, replay=True)
        on_shutdown(self.finalize)

    @property
    def client(self):
        return self._client

    @property
    def db(self):
        if self._db is not None:
            return self._db
        else:
            raise DataSourceNotReadyError()

    @staticmethod
    async def _get_db_version(db: AsyncIOMotorDatabase) -> int:
        version = await db["meta_info"].find_one({"key": "db_version"})
        if version is None:
            await db["meta_info"].insert_one({"key": "db_version", "value": 1})
            return 1
        else:
            return version["value"]

    @staticmethod
    async def _set_db_version(db_version: int, db: AsyncIOMotorDatabase):
        await db["meta_info"].update_one({"key": "db_version"},
                                         {"$set": {
                                             "value": db_version
                                         }},
                                         upsert=True)

    @staticmethod
    async def _ensure_index(db: AsyncIOMotorDatabase, coll_name: str, indexes: list[tuple[str, int]], **kwargs):
        try:
            await db[coll_name].create_index(indexes, **kwargs)
        except OperationFailure:
            logger.info(f"Index in {coll_name}: recreated")
            await db[coll_name].drop_index(indexes)
            await db[coll_name].create_index(indexes, **kwargs)

    @staticmethod
    async def _ensure_ttl_index(db: AsyncIOMotorDatabase, coll_name: str, expires_in: int):
        try:
            await db[coll_name].create_index([("update_time", 1)], expireAfterSeconds=expires_in)
        except OperationFailure:
            await db.command({
                "collMod": coll_name,
                "index": {
                    "keyPattern": {"update_time": 1},
                    "expireAfterSeconds": expires_in,
                }
            })
            logger.success(f"TTL Index in {coll_name}: expireAfterSeconds changed to {expires_in}")

    async def initialize(self):
        client = AsyncIOMotorClient(self.conf.pixiv_mongo_conn_url)
        options = CodecOptions(tz_aware=True)
        db = client[self.conf.pixiv_mongo_database_name].with_options(options)

        # migrate
        db_version = await self._get_db_version(db)
        await self.mongo_migration_mgr.perform_migration(db, db_version, self.app_db_version)
        await self._set_db_version(self.app_db_version, db)

        # ensure index
        await self._ensure_index(db, 'meta_info', [("key", 1)], unique=True)

        await self._ensure_index(db, 'pixiv_binding', [("adapter", 1), ("user_id", 1)], unique=True)

        await self._ensure_index(db, 'subscription', [("subscriber.adapter", 1)])
        await self._ensure_index(db, 'subscription', [("subscriber", 1),
                                                      ("type", 1)], unique=True)

        await self._ensure_index(db, 'watch_task', [("subscriber.adapter", 1)])
        await self._ensure_index(db, 'watch_task', [("subscriber.adapter", 1),
                                                    ("type", 1)])

        await self._ensure_index(db, 'local_tags', [("name", 1)], unique=True)
        await self._ensure_index(db, 'local_tags', [("translated_name", 1)])

        await self._ensure_index(db, 'download_cache', [("illust_id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'download_cache', self.conf.pixiv_download_cache_expires_in)

        await self._ensure_index(db, 'illust_detail_cache', [("illust.id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'illust_detail_cache', self.conf.pixiv_illust_detail_cache_expires_in)

        await self._ensure_index(db, 'user_detail_cache', [("user.id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'user_detail_cache', self.conf.pixiv_user_detail_cache_expires_in)

        await self._ensure_index(db, 'illust_ranking_cache', [("mode", 1)], unique=True)
        await self._ensure_ttl_index(db, 'illust_ranking_cache', self.conf.pixiv_illust_ranking_cache_expires_in)

        await self._ensure_index(db, 'search_illust_cache', [("word", 1)], unique=True)
        await self._ensure_ttl_index(db, 'search_illust_cache', self.conf.pixiv_search_illust_cache_expires_in)

        await self._ensure_index(db, 'search_user_cache', [("word", 1)], unique=True)
        await self._ensure_ttl_index(db, 'search_user_cache', self.conf.pixiv_search_user_cache_expires_in)

        await self._ensure_index(db, 'user_illusts_cache', [("user_id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'user_illusts_cache', self.conf.pixiv_user_illusts_cache_delete_in)

        await self._ensure_index(db, 'user_bookmarks_cache', [("user_id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'user_bookmarks_cache', self.conf.pixiv_user_bookmarks_cache_delete_in)

        await self._ensure_index(db, 'related_illusts_cache', [("original_illust_id", 1)], unique=True)
        await self._ensure_ttl_index(db, 'related_illusts_cache', self.conf.pixiv_related_illusts_cache_expires_in)

        await self._ensure_index(db, 'other_cache', [("type", 1)], unique=True)
        await self._ensure_ttl_index(db, 'other_cache', self.conf.pixiv_other_cache_expires_in)

        self._client = client
        self._db = db
        logger.success("MongoDataSource Initialization Succeed.")

    async def finalize(self):
        if self._client:
            self._client.close()
        self._client = None
        self._db = None


__all__ = ("MongoDataSource",)

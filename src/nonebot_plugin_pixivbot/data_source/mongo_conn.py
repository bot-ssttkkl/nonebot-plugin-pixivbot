from motor.motor_asyncio import AsyncIOMotorClient
from nonebot import logger, get_driver
from pymongo.errors import OperationFailure

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.utils.config import Config


@context.register_singleton()
class MongoConn:
    conf = context.require(Config)

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

    @staticmethod
    async def _ensure_cache_index(db, coll_name, identity_field, expires_in):
        db[coll_name].create_index([(identity_field, 1)], unique=True)

        try:
            await db[coll_name].create_index(
                [("update_time", 1)], expireAfterSeconds=expires_in)
        except OperationFailure:
            await db.command({
                "collMod": coll_name,
                "index": {
                    "keyPattern": {"update_time": 1},
                    "expireAfterSeconds": expires_in,
                }
            })
            logger.success(
                f"TTL Index ({coll_name}): expireAfterSeconds changed to {expires_in}")

    async def initialize(self):
        client = AsyncIOMotorClient(self.conf.pixiv_mongo_conn_url)
        db = client[self.conf.pixiv_mongo_database_name]

        # ensure index
        await self._ensure_cache_index(db, 'download_cache', "illust_id",
                                       self.conf.pixiv_download_cache_expires_in)
        await self._ensure_cache_index(db, 'illust_detail_cache', "illust.id",
                                       self.conf.pixiv_illust_detail_cache_expires_in)
        await self._ensure_cache_index(db, 'user_detail_cache', "user.id",
                                       self.conf.pixiv_user_detail_cache_expires_in)
        await self._ensure_cache_index(db, 'illust_ranking_cache', "mode",
                                       self.conf.pixiv_illust_ranking_cache_expires_in)
        await self._ensure_cache_index(db, 'search_illust_cache', "word",
                                       self.conf.pixiv_search_illust_cache_expires_in)
        await self._ensure_cache_index(db, 'search_user_cache', "word",
                                       self.conf.pixiv_search_user_cache_expires_in)
        await self._ensure_cache_index(db, 'user_illusts_cache', "user_id",
                                       self.conf.pixiv_user_illusts_cache_expires_in)
        await self._ensure_cache_index(db, 'user_bookmarks_cache', "user_id",
                                       self.conf.pixiv_user_bookmarks_cache_expires_in)
        await self._ensure_cache_index(db, 'related_illusts_cache', "original_illust_id",
                                       self.conf.pixiv_related_illusts_cache_expires_in)
        await self._ensure_cache_index(db, 'other_cache', "type",
                                       self.conf.pixiv_other_cache_expires_in)

        try:
            await db['pixiv_binding'].create_index([("qq_id", 1)], unique=True)

            await db['subscription'].create_index([("user_id", 1)])
            await db['subscription'].create_index([("group_id", 1)])
            await db['subscription'].create_index([("type", 1), ("user_id", 1)])
            await db['subscription'].create_index([("type", 1), ("group_id", 1)])

            await db['local_tags'].create_index([("name", 1)], unique=True)
            await db['local_tags'].create_index([("translated_name", 1)])
            logger.info("ensure indexes completed")
        except Exception as e:
            logger.exception(e)
            logger.warning("Error occured during creating indexes.")

        self._client = client
        self._db = db

    async def finalize(self):
        self._client.close()
        self._client = None
        self._db = None


__all__ = ("MongoConn",)

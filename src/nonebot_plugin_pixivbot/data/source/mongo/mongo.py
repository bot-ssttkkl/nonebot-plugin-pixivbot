from asyncio import create_task, gather
from typing import List, Type

from beanie import init_beanie, Document
from bson import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from nonebot import logger
from pymongo import IndexModel
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

        self.document_models: List[Type[Document]] = []

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
    async def _raw_get_db_version(db: AsyncIOMotorDatabase) -> int:
        version = await db["meta_info"].find_one({"key": "db_version"})
        if version is None:
            await db["meta_info"].insert_one({"key": "db_version", "value": 1})
            return 1
        else:
            return version["value"]

    @staticmethod
    async def _raw_set_db_version(db: AsyncIOMotorDatabase, db_version: int):
        await db["meta_info"].update_one({"key": "db_version"},
                                         {"$set": {
                                             "value": db_version
                                         }},
                                         upsert=True)

    @staticmethod
    async def _ensure_ttl_index(db: AsyncIOMotorDatabase, coll_name: str, index: IndexModel):
        try:
            await db[coll_name].create_indexes([index])
        except OperationFailure:
            await db.command({
                "collMod": coll_name,
                "index": {
                    "keyPattern": index.document["key"],
                    "expireAfterSeconds": index.document["expireAfterSeconds"]
                }
            })
            logger.success(
                f"Index in {coll_name}: expireAfterSeconds changed to {index.document['expireAfterSeconds']}")

    async def initialize(self):
        client = AsyncIOMotorClient(self.conf.pixiv_mongo_conn_url)
        options = CodecOptions(tz_aware=True)
        db = client[self.conf.pixiv_mongo_database_name].with_options(options)

        # migrate
        db_version = await self._raw_get_db_version(db)
        await self.mongo_migration_mgr.perform_migration(db, db_version, self.app_db_version)
        await self._raw_set_db_version(db, self.app_db_version)

        # ensure ttl indexes (before init beanie)
        index_tasks = []
        for model in self.document_models:
            name = model.__name__

            settings = getattr(model, "Settings", None)
            if settings:
                settings_name = getattr(settings, "name")
                if settings_name:
                    name = settings_name

                settings_indexes = getattr(settings, "indexes")
                if settings_indexes:
                    for index in settings_indexes:
                        if isinstance(index, IndexModel) and index.document.get("expireAfterSeconds", None):
                            index_tasks.append(create_task(self._ensure_ttl_index(db, name, index)))
        await gather(*index_tasks)

        await init_beanie(database=db, document_models=self.document_models, allow_index_dropping=True)

        self._client = client
        self._db = db
        logger.success("MongoDataSource Initialization Succeed.")

    async def finalize(self):
        if self._client:
            self._client.close()
        self._client = None
        self._db = None


__all__ = ("MongoDataSource",)

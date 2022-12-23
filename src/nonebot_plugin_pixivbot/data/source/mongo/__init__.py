from asyncio import create_task, gather
from contextlib import asynccontextmanager
from typing import List, Type

from beanie import init_beanie, Document
from bson import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from nonebot import logger
from pymongo import IndexModel
from pymongo.errors import OperationFailure

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.errors import DataSourceNotReadyError
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.lifecycler import on_shutdown, on_startup
from ..lifecycle_mixin import DataSourceLifecycleMixin


@context.inject
class MongoDataSource(DataSourceLifecycleMixin):
    conf = Inject(Config)
    app_db_version = 7

    def __init__(self):
        super().__init__()

        self._client = None
        self._db = None

        self.document_models: List[Type[Document]] = []

        on_startup(replay=True)(self.initialize)
        on_shutdown()(self.close)

    @property
    def client(self):
        if self._client is None:
            raise DataSourceNotReadyError()

        return self._client

    @property
    def db(self):
        if self._db is None:
            raise DataSourceNotReadyError()

        return self._db

    async def _raw_get_db_version(self, db: AsyncIOMotorDatabase) -> int:
        blank_database = "subscription" not in (await db.list_collection_names())
        if blank_database:
            await db["meta_info"].insert_one({"key": "db_version", "value": self.app_db_version})
            return self.app_db_version
        else:
            version = await db["meta_info"].find_one({"key": "db_version"})
            if version is None:
                await db["meta_info"].insert_one({"key": "db_version", "value": 1})
                return 1
            else:
                return version["value"]


    async def _raw_set_db_version(self, db: AsyncIOMotorDatabase, db_version: int):
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
        from .migration import MongoMigrationManager

        await self._fire_initializing()

        client = AsyncIOMotorClient(self.conf.pixiv_mongo_conn_url)
        options = CodecOptions(tz_aware=True)
        db = client[self.conf.pixiv_mongo_database_name].with_options(options)

        # migrate
        mig_mgr = MongoMigrationManager(lambda prev, cur: self._raw_set_db_version(db, cur))
        db_version = await self._raw_get_db_version(db)
        await mig_mgr.perform_migration(db, db_version, self.app_db_version)

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

        await self._fire_initialized()
        logger.success("MongoDataSource Initialized.")

    async def close(self):
        await self._fire_closing()

        if self._client:
            self._client.close()
        self._client = None
        self._db = None

        await self._fire_closed()
        logger.success("MongoDataSource Disposed.")

    @asynccontextmanager
    async def start_session(self):
        if self._client is None:
            raise DataSourceNotReadyError()
        session = await self._client.start_session()
        yield session
        session.end_session()


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    context.register_eager_singleton()(MongoDataSource)

__all__ = ("MongoDataSource",)

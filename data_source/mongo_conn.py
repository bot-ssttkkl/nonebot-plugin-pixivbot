from motor.motor_asyncio import AsyncIOMotorClient
from nonebot import logger, get_driver

from .pkg_context import context
from ..config import Config

import pymongo

conf: Config = context.require(Config)

_mongodb_client: AsyncIOMotorClient = None


def db():
    return _mongodb_client[conf.pixiv_mongo_database_name]


async def _ensure_cache_index(db, coll_name, identity_field, expires_in):
    db[coll_name].create_index([(identity_field, 1)], unique=True)

    try:
        await db[coll_name].create_index(
            [("update_time", 1)], expireAfterSeconds=expires_in)
    except pymongo.errors.OperationFailure as e:
        await db.command({
            "collMod": coll_name,
            "index": {
                "keyPattern": {"update_time": 1},
                "expireAfterSeconds": expires_in,
            }
        })
        logger.success(
            f"TTL Index ({coll_name}): expireAfterSeconds changed to {expires_in}")


@get_driver().on_startup
async def connect_to_mongodb():
    global _mongodb_client
    _mongodb_client = AsyncIOMotorClient(
        f'{conf.pixiv_mongo_conn_url}/{conf.pixiv_mongo_database_name}')

    # ensure index
    db = _mongodb_client[conf.pixiv_mongo_database_name]
    await _ensure_cache_index(db, 'download_cache', "illust_id", conf.pixiv_download_cache_expires_in)
    await _ensure_cache_index(db, 'illust_detail_cache', "illust.id", conf.pixiv_illust_detail_cache_expires_in)
    await _ensure_cache_index(db, 'user_detail_cache', "user.id", conf.pixiv_user_detail_cache_expires_in)
    await _ensure_cache_index(db, 'illust_ranking_cache', "mode", conf.pixiv_illust_ranking_cache_expires_in)
    await _ensure_cache_index(db, 'search_illust_cache', "word", conf.pixiv_search_illust_cache_expires_in)
    await _ensure_cache_index(db, 'search_user_cache', "word", conf.pixiv_search_user_cache_expires_in)
    await _ensure_cache_index(db, 'user_illusts_cache', "user_id", conf.pixiv_user_illusts_cache_expires_in)
    await _ensure_cache_index(db, 'user_bookmarks_cache', "user_id", conf.pixiv_user_bookmarks_cache_expires_in)
    await _ensure_cache_index(db, 'related_illusts_cache',
                              "original_illust_id", conf.pixiv_related_illusts_cache_expires_in)
    await _ensure_cache_index(db, 'other_cache', "type", conf.pixiv_other_cache_expires_in)

    try:
        await db['pixiv_binding'].create_index([("qq_id", 1)], unique=True)

        await db['subscription'].create_index([("user_id", 1)])
        await db['subscription'].create_index([("group_id", 1)])
        await db['subscription'].create_index([("type", 1), ("user_id", 1)])
        await db['subscription'].create_index([("type", 1), ("group_id", 1)])

        await db['local_tags'].create_index([("name", 1)], unique=True)
        await db['local_tags'].create_index([("translated_name", 1)])
    except Exception as e:
        logger.exception(e)
        logger.warning("Error occured during creating indexes.")


@get_driver().on_shutdown
async def free_conn():
    global _mongodb_client
    if _mongodb_client is not None:
        _mongodb_client.close()


__all__ = ("db", "connect_to_mongodb", "free_conn")

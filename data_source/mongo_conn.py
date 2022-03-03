from motor.motor_asyncio import AsyncIOMotorClient
from nonebot import logger, get_driver

from ..config import conf

_mongodb_client: AsyncIOMotorClient = None


def db():
    return _mongodb_client[conf.pixiv_mongo_database_name]


@get_driver().on_startup
async def connect_to_mongodb():
    global _mongodb_client
    _mongodb_client = AsyncIOMotorClient(f'{conf.pixiv_mongo_conn_url}/{conf.pixiv_mongo_database_name}')
    logger.opt(colors=True).info("<y>Connect to Mongodb</y>")

    # ensure index
    try:
        db = _mongodb_client[conf.pixiv_mongo_database_name]

        db['pixiv_binding'].create_index([("qq_id", 1)], unique=True)

        db['subscription'].create_index([("user_id", 1)])
        db['subscription'].create_index([("group_id", 1)])
        db['subscription'].create_index([("type", 1), ("user_id", 1)])
        db['subscription'].create_index([("type", 1), ("group_id", 1)])

        db['download_cache'].create_index([("illust_id", 1)], unique=True)
        db['download_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24 * 7)

        db['illust_detail_cache'].create_index([("illust.id", 1)], unique=True)
        db['illust_detail_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24 * 7)

        db['illust_ranking_cache'].create_index([("mode", 1)], unique=True)
        db['illust_ranking_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 6)

        db['search_illust_cache'].create_index([("word", 1)], unique=True)
        db['search_illust_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24)

        db['search_user_cache'].create_index([("word", 1)], unique=True)
        db['search_user_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24)

        db['user_illusts_cache'].create_index([("user_id", 1)], unique=True)
        db['user_illusts_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24)

        db['user_bookmarks_cache'].create_index([("user_id", 1)], unique=True)
        db['user_bookmarks_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24)

        db['related_illusts_cache'].create_index([("illust_id", 1)], unique=True)
        db['related_illusts_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 24)

        db['other_cache'].create_index([("type", 1)], unique=True)
        db['other_cache'].create_index([("update_time", 1)], expireAfterSeconds=3600 * 6)
    except Exception as e:
        logger.exception(e)
        logger.warning("Error occured during creating indexes.")


@get_driver().on_shutdown
async def free_conn():
    global _mongodb_client
    if _mongodb_client is not None:
        _mongodb_client.close()
        logger.opt(colors=True).info("<y>Disconnect to Mongodb</y>")


__all__ = ("db", "connect_to_mongodb", "free_conn")

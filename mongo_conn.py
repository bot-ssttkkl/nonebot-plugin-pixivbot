from motor.motor_asyncio import AsyncIOMotorClient
from nonebot import logger, get_driver

from .config import conf

_mongodb_client: AsyncIOMotorClient = None


def mongo_client():
    return _mongodb_client


@get_driver().on_startup
async def connect_to_mongodb():
    global _mongodb_client
    _mongodb_client = AsyncIOMotorClient(conf.pixiv_mongo_conn_url)
    logger.opt(colors=True).info("<y>Connect to Mongodb</y>")


@get_driver().on_shutdown
async def free_conn():
    global _mongodb_client
    if _mongodb_client is not None:
        _mongodb_client.close()
        logger.opt(colors=True).info("<y>Disconnect to Mongodb</y>")


__all__ = ("mongo_client", "connect_to_mongodb", "free_conn")

# import nonebot
from datetime import datetime, timedelta

from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver, require
from nonebot.log import logger

from . import handler
from .config import conf
from .data_source import data_source
from .model import *


@get_driver().on_startup
async def initialize_data_src():
    await data_source.initialize(db_name=conf.pixiv_mongo_database_name,
                                 proxy=conf.pixiv_proxy,
                                 timeout=conf.pixiv_query_timeout,
                                 compression_enabled=conf.pixiv_compression_enabled,
                                 compression_max_size=conf.pixiv_compression_max_size,
                                 compression_quantity=conf.pixiv_compression_quantity)


get_driver().on_shutdown(data_source.shutdown)


@get_driver().on_startup
async def do_refresh():
    try:
        result = await data_source.refresh(conf.pixiv_refresh_token)
        logger.info(f"refresh access token successfully. new token expires in {result.expires_in} seconds.")
        logger.debug(f"access_token: {result.access_token}")
        logger.debug(f"refresh_token: {result.refresh_token}")
        if result.refresh_token != conf.pixiv_refresh_token:
            logger.warning(f"refresh token has been changed: {result.refresh_token}")

        next_time = datetime.now() + timedelta(seconds=result.expires_in * 0.8)

        scheduler = require("nonebot_plugin_apscheduler").scheduler
        scheduler.add_job(do_refresh, trigger=DateTrigger(next_time))
    except Exception as e:
        logger.exception(e)


__all__ = tuple()

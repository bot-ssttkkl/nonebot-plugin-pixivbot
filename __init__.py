# import nonebot
from datetime import datetime, timedelta

from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver, require
from nonebot.log import logger

from . import handler
from .config import Config
from .model import *
from .data_source import data_source

global_config = get_driver().config
config = Config(**global_config.dict())

data_source.mongodb_name = config.pixiv_mongodb_name

get_driver().on_startup(data_source.initialize)
get_driver().on_shutdown(data_source.shutdown)


@get_driver().on_startup
async def do_refresh():
    try:
        result = await data_source.refresh(config.pixiv_refresh_token)
        logger.info(f"refresh access token successfully. new token expires in {result.expires_in} seconds.")
        if result.refresh_token != config.pixiv_refresh_token:
            logger.warning(f"refresh token has been changed: {result.refresh_token}")

        next_time = datetime.now() + timedelta(seconds=result.expires_in * 0.8)

        scheduler = require("nonebot_plugin_apscheduler").scheduler
        scheduler.add_job(do_refresh, trigger=DateTrigger(next_time))
    except Exception as e:
        logger.exception(e)

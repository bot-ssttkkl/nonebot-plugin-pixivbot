# import nonebot
from datetime import datetime, timedelta

from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver, require
from nonebot.log import logger

from . import handler
from . import pixiv
from .config import Config
from .model import *
from .pixiv import api as papi

global_config = get_driver().config
config = Config(**global_config.dict())

get_driver().on_startup(pixiv.initialize)


@get_driver().on_startup
async def do_refresh():
    result = await pixiv.get_refresh_token(config.pixiv_refresh_token)

    if result.has_error:
        logger.warning(f"error occurred when refresh access token: {result}")
    else:
        papi().set_auth(result.access_token, result.refresh_token)
        logger.info(f"refresh access token successfully. new token expires in {result.expires_in} seconds.")
        if result.refresh_token != config.pixiv_refresh_token:
            logger.warning(f"refresh token has been changed: {result.refresh_token}")

    next_time = datetime.now() + timedelta(seconds=result.expires_in * 0.8)

    scheduler = require("nonebot_plugin_apscheduler").scheduler
    scheduler.add_job(do_refresh, trigger=DateTrigger(next_time))


@get_driver().on_shutdown
async def on_shutdown():
    await pixiv.shutdown()

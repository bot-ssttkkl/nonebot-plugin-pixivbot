"""
nonebot-plugin-pixivbot

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""

# =========== require dependency ============
from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_access_control")
require("nonebot_plugin_session")
require("nonebot_plugin_session_orm")
require("nonebot_plugin_session_saa")
require("nonebot_plugin_saa")
require("nonebot_plugin_localstore")
require("ssttkkl_nonebot_utils")

# =========== plugin meta ============
from nonebot import logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import __plugin_meta__ as saa_meta

from .config import Config
from .usage import usage

__plugin_meta__ = PluginMetadata(
    name='PixivBot',
    description='发送随机Pixiv插画、画师更新推送、定时订阅推送……',
    usage=usage,
    type="application",
    homepage="https://github.com/bot-ssttkkl/nonebot-plugin-pixivbot",
    config=Config,
    supported_adapters=saa_meta.supported_adapters
)

# =========== register handler & service ============
from ssttkkl_nonebot_utils.config_loader import ConfigError

try:
    from . import service
    from . import handler
except ConfigError as e:
    logger.error(e)

__all__ = ("context", "__plugin_meta__")

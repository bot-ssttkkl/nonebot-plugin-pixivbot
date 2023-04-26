"""
nonebot-plugin-pixivbot

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""
from nonebot.plugin import PluginMetadata

from .handler.command.help import help_text

__plugin_meta__ = PluginMetadata(
    name='PixivBot',
    description='发送随机Pixiv插画、画师更新推送、定时订阅推送……',
    usage=help_text,
    extra={'version': '1.4.0'}
)

# =========== require dependency ============
from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_access_control")

# =========== register handler & service ============
from . import handler
from . import service

# ============== load submodule =============
from nonebot import get_driver, load_plugin

supported_adapters = {
    "OneBot V11": "nonebot_plugin_pixivbot_onebot_v11",
    "Kaiheila": "nonebot_plugin_pixivbot_kook",
    "Telegram": "nonebot_plugin_pixivbot_telegram"
}

driver = get_driver()
for adapter in driver._adapters:
    if adapter in supported_adapters:
        load_plugin(supported_adapters[adapter])

__all__ = ("context", "__plugin_meta__")

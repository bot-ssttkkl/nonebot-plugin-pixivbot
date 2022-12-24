"""
nonebot-plugin-pixivbot

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot
"""
from .utils.nonebot import default_command_start

help_text = f"""
常规语句：
- 看看榜<范围>：查看pixiv榜单
- 来张图：从推荐插画随机抽选一张插画
- 来张<关键字>图：搜索关键字，从搜索结果随机抽选一张插画
- 来张<用户>老师的图：搜索画师，从该画师的插画列表里随机抽选一张插画
- 看看图<插画ID>：查看id为<插画ID>的插画
- 来张私家车：从书签中随机抽选一张插画
- 还要：重复上一次请求
- 不够色：获取上一张插画的相关推荐

命令语句：
- {default_command_start}pixivbot help：查看本帮助
- {default_command_start}pixivbot bind：绑定Pixiv账号

更多功能：参见https://github.com/ssttkkl/nonebot-plugin-pixivbot
""".strip()

from nonebot.plugin import PluginMetadata

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

# ============== load custom protocol =============
from importlib import import_module
from nonebot import logger, get_driver

supported_modules = {
    "OneBot V11": "nonebot_plugin_pixivbot_onebot_v11",
    "Kaiheila": "nonebot_plugin_pixivbot_kook",
    "Telegram": "nonebot_plugin_pixivbot_telegram"
}

loaded_modules = []

driver = get_driver()
for adapter in driver._adapters:
    if adapter in supported_modules:
        import_module(supported_modules[adapter])
        loaded_modules.append(adapter)
        logger.debug(f"Succeeded to load PixivBot for {adapter}")

if len(loaded_modules):
    logger.success(f"Loaded PixivBot for {', '.join(loaded_modules)}")

__all__ = ("context", "__plugin_meta__")

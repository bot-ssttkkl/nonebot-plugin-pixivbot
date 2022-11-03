from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType

conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    try:
        import beanie
        import motor
    except ImportError as e:
        raise RuntimeError("若需要使用MongoDB，请安装nonebot-plugin-pixivbot[mongo]") from e

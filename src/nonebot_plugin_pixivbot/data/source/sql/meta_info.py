from sqlalchemy import Column, String

from nonebot_plugin_pixivbot.data.source import SqlDataSource
from nonebot_plugin_pixivbot.global_context import context


@context.require(SqlDataSource).registry.mapped
class MetaInfo:
    __tablename__ = "meta_info"

    key: str = Column("key", String, primary_key=True)
    value: str = Column("value", String, nullable=False)

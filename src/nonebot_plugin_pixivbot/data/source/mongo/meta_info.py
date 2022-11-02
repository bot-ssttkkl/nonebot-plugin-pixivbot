from typing import Any

from beanie import Document
from pymongo import IndexModel

from nonebot_plugin_pixivbot import context
from . import MongoDataSource


class MetaInfo(Document):
    key: str
    value: Any

    class Settings:
        name = "meta_info"
        indexes = [
            IndexModel([("key", 1)], unique=True),
        ]


context.require(MongoDataSource).document_models.append(MetaInfo)

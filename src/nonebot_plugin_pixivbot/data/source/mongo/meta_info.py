from typing import Any

from pymongo import IndexModel

from . import MongoDocument


class MetaInfo(MongoDocument):
    key: str
    value: Any

    class Settings:
        name = "meta_info"
        indexes = [
            IndexModel([("key", 1)], unique=True),
        ]

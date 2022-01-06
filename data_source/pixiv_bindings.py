import typing

from pymongo import MongoClient

from ..config import conf
from .mongo_conn import mongo_client


class PixivBindings:
    db_name: str

    def __init__(self, db_name: str):
        self.db_name = db_name

    @property
    def _db(self) -> MongoClient:
        return mongo_client()[self.db_name]

    async def bind(self, qq_id: int, pixiv_user_id: int) -> None:
        await self._db.pixiv_binding.update_one({"qq_id": qq_id},
                                                {"$set": {
                                                    "pixiv_user_id": pixiv_user_id
                                                }},
                                                upsert=True)

    async def unbind(self, qq_id: int) -> None:
        await self._db.pixiv_binding.delete_one({"qq_id": qq_id})

    async def get_binding(self, qq_id: int) -> typing.Optional[int]:
        result = await self._db.pixiv_binding.find_one({"qq_id": qq_id})
        if result is None:
            return None
        else:
            return result["pixiv_user_id"]


pixiv_bindings = PixivBindings(db_name=conf.pixiv_mongo_database_name)

__all__ = ("PixivBindings", "pixiv_bindings")

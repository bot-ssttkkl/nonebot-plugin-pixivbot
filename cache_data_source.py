import typing
from datetime import datetime

import bson

from .model.Illust import Illust
from .model.User import User
from .mongo_conn import mongo_client


class CacheDataSource:
    db_name: str

    def __init__(self, db_name):
        self.db_name = db_name

    @property
    def _db(self):
        return mongo_client()[self.db_name]

    def _illusts_cache_loader_factory(self, collection_name: str,
                                      arg_name: str,
                                      arg: typing.Any):
        async def cache_loader() -> typing.Optional[typing.List[int]]:
            cache = await self._db[collection_name].find_one({arg_name: arg})
            if cache is not None:
                return cache["illust_id"]
            else:
                return None

        return cache_loader

    def _illusts_cache_updater_factory(self, collection_name: str,
                                       arg_name: str,
                                       arg: typing.Any):
        async def cache_updater(content: typing.List[int]):
            await self._db[collection_name].update_one(
                {arg_name: arg},
                {"$set": {
                    "illust_id": content,
                    "update_time": datetime.now()
                }},
                upsert=True
            )

        return cache_updater

    async def illust_detail(self, illust_id: int) -> typing.Optional[Illust]:
        cache = await self._db.illust_detail_cache.find_one({"illust.id": illust_id})
        if cache is not None:
            return Illust.parse_obj(cache["illust"])
        else:
            return None

    async def update_illust_detail(self, illust: Illust):
        await self._db.illust_detail_cache.update_one(
            {"illust.id": illust.id},
            {"$set": {
                "illust": illust.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    def search_illust(self, word: str):
        return self._illusts_cache_loader_factory(
            "search_illust_cache", "word", word)()

    def update_search_illust(self, word: str, content: typing.List[int]):
        return self._illusts_cache_updater_factory(
            "search_illust_cache", "word", word)(content)

    def user_illusts(self, user_id: int):
        return self._illusts_cache_loader_factory(
            "user_illusts_cache", "user_id", user_id)()

    def update_user_illusts(self, user_id: int, content: typing.List[int]):
        return self._illusts_cache_updater_factory(
            "user_illusts_cache", "user_id", user_id)(content)

    def user_bookmarks(self, user_id: int):
        return self._illusts_cache_loader_factory(
            "user_bookmarks_cache", "user_id", user_id)()

    def update_user_bookmarks(self, user_id: int, content: typing.List[int]):
        return self._illusts_cache_updater_factory(
            "user_bookmarks_cache", "user_id", user_id)(content)

    def recommended_illusts(self):
        return self._illusts_cache_loader_factory(
            "other_cache", "type", "recommended_illusts")()

    def update_recommended_illusts(self, content: typing.List[int]):
        return self._illusts_cache_updater_factory(
            "other_cache", "type", "recommended_illusts")(content)

    def illust_ranking(self, mode: str):
        return self._illusts_cache_loader_factory(
            "other_cache", "type", mode + "_ranking")()

    def update_illust_ranking(self, mode: str, content: typing.List[int]):
        return self._illusts_cache_updater_factory(
            "other_cache", "type", mode + "_ranking")(content)

    async def search_user(self, word: str) -> typing.Optional[typing.List[User]]:
        cache = await self._db.search_user_cache.find_one({"word": word})
        if cache is not None:
            return [User.parse_obj(x) for x in cache["users"]]
        else:
            return None

    async def update_search_user(self, word: str, content: typing.List[User]):
        now = datetime.now()
        await self._db.search_user_cache.update_one(
            {"word": word},
            {"$set": {
                "users": [x.dict() for x in content],
                "update_time": now
            }},
            upsert=True
        )

    async def download(self, illust_id: int) -> typing.Optional[bytes]:
        cache = await self._db.download_cache.find_one({"illust_id": illust_id})
        if cache is not None:
            return cache["content"]
        else:
            return None

    async def update_download(self, illust_id: int, content: bytes):
        now = datetime.now()
        await self._db.download_cache.update_one(
            {"illust_id": illust_id},
            {"$set": {
                "content": bson.Binary(content),
                "update_time": now
            }},
            upsert=True
        )

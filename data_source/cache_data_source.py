import typing
from datetime import datetime

import bson

from ..model import Illust, User, LazyIllust
from .mongo_conn import db

from pymongo import UpdateOne
from nonebot import logger

class CacheDataSource:
    def _make_illusts_cache_loader(self, collection_name: str,
                                   arg_name: str,
                                   arg: typing.Any):
        async def cache_loader() -> typing.Optional[typing.List[LazyIllust]]:
            result = db()[collection_name].aggregate([
                {
                    "$match": {arg_name: arg}
                },
                {
                    "$replaceWith": {"illust_id": "$illust_id"}
                },
                {
                    "$unwind": "$illust_id"
                },
                {
                    "$lookup": {
                        "from": "illust_detail_cache",
                        "localField": "illust_id",
                        "foreignField": "illust.id",
                        "as": "illusts"
                    }
                },
                {
                    "$replaceWith": {
                        "$mergeObjects": [
                            "$$ROOT",
                            {"$arrayElemAt": ["$illusts", 0]}
                        ]
                    }
                },
                {
                    "$project": {"_id": 0, "illust": 1, "illust_id": 1}
                }
            ])

            cache = []
            # broken = 0
            async for x in result:
                if "illust" in x and x["illust"] is not None:
                    cache.append(LazyIllust(
                        x["illust_id"], Illust.parse_obj(x["illust"])))
                else:
                    cache.append(LazyIllust(x["illust_id"]))
                    # broken += 1

            # logger.info(
            #     f"{len(cache)} got, illust_detail of {broken} are missed")

            if len(cache) != 0:
                return cache
            else:
                return None

        return cache_loader

    def _make_illusts_cache_updater(self, collection_name: str,
                                    arg_name: str,
                                    arg: typing.Any):
        async def cache_updater(content: typing.List[typing.Union[Illust, LazyIllust]]):
            now = datetime.now()
            await db()[collection_name].update_one(
                {arg_name: arg},
                {"$set": {
                    "illust_id": [illust.id for illust in content],
                    "update_time": now
                }},
                upsert=True
            )

            opt = []
            for illust in content:
                if isinstance(illust, LazyIllust) and illust.content is not None:
                    illust = illust.content

                if isinstance(illust, Illust):
                    opt.append(UpdateOne(
                        {"illust.id": illust.id},
                        {"$set": {
                            "illust": illust.dict(),
                            "update_time": now
                        }},
                        upsert=True
                    ))
            if len(opt) != 0:
                await db().illust_detail_cache.bulk_write(opt, ordered=False)

        return cache_updater

    async def illust_detail(self, illust_id: int) -> typing.Optional[Illust]:
        cache = await db().illust_detail_cache.find_one({"illust.id": illust_id})
        if cache is not None:
            return Illust.parse_obj(cache["illust"])
        else:
            return None

    async def update_illust_detail(self, illust: Illust):
        await db().illust_detail_cache.update_one(
            {"illust.id": illust.id},
            {"$set": {
                "illust": illust.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    def search_illust(self, word: str):
        return self._make_illusts_cache_loader(
            "search_illust_cache", "word", word)()

    def update_search_illust(self, word: str, content: typing.Union[Illust, LazyIllust]):
        return self._make_illusts_cache_updater(
            "search_illust_cache", "word", word)(content)

    def user_illusts(self, user_id: int):
        return self._make_illusts_cache_loader(
            "user_illusts_cache", "user_id", user_id)()

    def update_user_illusts(self, user_id: int, content: typing.Union[Illust, LazyIllust]):
        return self._make_illusts_cache_updater(
            "user_illusts_cache", "user_id", user_id)(content)

    def user_bookmarks(self, user_id: int):
        return self._make_illusts_cache_loader(
            "user_bookmarks_cache", "user_id", user_id)()

    def update_user_bookmarks(self, user_id: int, content: typing.Union[Illust, LazyIllust]):
        return self._make_illusts_cache_updater(
            "user_bookmarks_cache", "user_id", user_id)(content)

    def recommended_illusts(self):
        return self._make_illusts_cache_loader(
            "other_cache", "type", "recommended_illusts")()

    def update_recommended_illusts(self, content: typing.Union[Illust, LazyIllust]):
        return self._make_illusts_cache_updater(
            "other_cache", "type", "recommended_illusts")(content)

    def illust_ranking(self, mode: str):
        return self._make_illusts_cache_loader(
            "other_cache", "type", mode + "_ranking")()

    def update_illust_ranking(self, mode: str, content: typing.Union[Illust, LazyIllust]):
        return self._make_illusts_cache_updater(
            "other_cache", "type", mode + "_ranking")(content)

    async def search_user(self, word: str) -> typing.Optional[typing.List[User]]:
        cache = await db().search_user_cache.find_one({"word": word})
        if cache is not None:
            return [User.parse_obj(x) for x in cache["users"]]
        else:
            return None

    async def update_search_user(self, word: str, content: typing.List[User]):
        now = datetime.now()
        await db().search_user_cache.update_one(
            {"word": word},
            {"$set": {
                "users": [x.dict() for x in content],
                "update_time": now
            }},
            upsert=True
        )

    async def download(self, illust_id: int) -> typing.Optional[bytes]:
        cache = await db().download_cache.find_one({"illust_id": illust_id})
        if cache is not None:
            return cache["content"]
        else:
            return None

    async def update_download(self, illust_id: int, content: bytes):
        now = datetime.now()
        await db().download_cache.update_one(
            {"illust_id": illust_id},
            {"$set": {
                "content": bson.Binary(content),
                "update_time": now
            }},
            upsert=True
        )

    async def invalidate_cache(self):
        await db().download_cache.delete_many({})
        await db().illust_detail_cache.delete_many({})
        await db().illust_ranking_cache.delete_many({})
        await db().search_illust_cache.delete_many({})
        await db().search_user_cache.delete_many({})
        await db().user_illusts_cache.delete_many({})
        await db().user_bookmarks_cache.delete_many({})
        await db().other_cache.delete_many({})

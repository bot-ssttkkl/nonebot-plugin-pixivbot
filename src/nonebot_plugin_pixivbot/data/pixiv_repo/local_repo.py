import typing
from datetime import datetime

import bson
from nonebot import logger
from pymongo import UpdateOne

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo
from .lazy_illust import LazyIllust
from .pkg_context import context
from ..source import MongoDataSource


@context.register_singleton()
class LocalPixivRepo(AbstractPixivRepo):
    def __init__(self):
        self.mongo = context.require(MongoDataSource)

    def _make_illusts_cache_loader(self, collection_name: str, arg_name: str, arg: typing.Any, *, skip: int = 0,
                                   limit: int = 0):
        async def cache_loader() -> typing.Optional[typing.List[LazyIllust]]:
            aggregation = [
                {
                    "$match": {arg_name: arg}
                },
                {
                    "$replaceWith": {"illust_id": "$illust_id"}
                },
                {
                    "$unwind": "$illust_id"
                },
            ]

            if skip:
                aggregation.append({"$skip": skip})
            if limit:
                aggregation.append({"$limit": limit})

            aggregation.extend([
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

            result = self.mongo.db[collection_name].aggregate(aggregation)

            cache = []
            broken = 0
            async for x in result:
                if "illust" in x and x["illust"] is not None:
                    cache.append(LazyIllust(
                        x["illust_id"], Illust.parse_obj(x["illust"])))
                else:
                    cache.append(LazyIllust(x["illust_id"]))
                    broken += 1

            logger.info(
                f"[cache] {len(cache)} got, illust_detail of {broken} are missed")

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
            await self.mongo.db[collection_name].update_one(
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
                await self.mongo.db.illust_detail_cache.bulk_write(opt, ordered=False)

        return cache_updater

    async def illust_detail(self, illust_id: int) -> typing.Optional[Illust]:
        cache = await self.mongo.db.illust_detail_cache.find_one({"illust.id": illust_id})
        if cache is not None:
            return Illust.parse_obj(cache["illust"])
        else:
            return None

    async def update_illust_detail(self, illust: Illust):
        await self.mongo.db.illust_detail_cache.update_one(
            {"illust.id": illust.id},
            {"$set": {
                "illust": illust.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    async def user_detail(self, user_id: int) -> typing.Optional[User]:
        cache = await self.mongo.db.user_detail_cache.find_one({"user.id": user_id})
        if cache is not None:
            return User.parse_obj(cache["user"])
        else:
            return None

    async def update_user_detail(self, user: User):
        await self.mongo.db.user_detail_cache.update_one(
            {"user.id": user.id},
            {"$set": {
                "user": user.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    def search_illust(self, word: str, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("search_illust_cache", "word", word, skip=skip, limit=limit)()

    def update_search_illust(self, word: str, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("search_illust_cache", "word", word)(content)

    async def search_user(self, word: str, *, skip: int = 0, limit: int = 0) -> typing.Optional[typing.List[User]]:
        aggregation = [
            {
                "$match": {"word": word}
            },
            {
                "$replaceWith": {"user_id": "$user_id"}
            },
            {
                "$unwind": "$user_id"
            },
        ]

        if skip:
            aggregation.append({"$skip": skip})
        if limit:
            aggregation.append({"$limit": limit})

        aggregation.extend([
            {
                "$lookup": {
                    "from": "user_detail_cache",
                    "localField": "user_id",
                    "foreignField": "user.id",
                    "as": "users"
                }
            },
            {
                "$replaceWith": {
                    "$mergeObjects": [
                        "$$ROOT",
                        {"$arrayElemAt": ["$users", 0]}
                    ]
                }
            },
            {
                "$project": {"_id": 0, "user": 1, "user_id": 1}
            }
        ])

        result = self.mongo.db.search_user_cache.aggregate(aggregation)

        users = []
        async for x in result:
            if "user" in x and x["user"] is not None:
                users.append(User.parse_obj(x["user"]))
            else:
                users.append(User(id=x["user_id"], name="", account=""))

        if len(users) != 0:
            return users
        else:
            return None

    async def update_search_user(self, word: str, content: typing.List[User]):
        now = datetime.now()
        await self.mongo.db.search_user_cache.update_one(
            {"word": word},
            {"$set": {
                "user_id": [user.id for user in content],
                "update_time": now
            }},
            upsert=True
        )

        opt = []
        for user in content:
            opt.append(UpdateOne(
                {"user.id": user.id},
                {"$set": {
                    "user": user.dict(),
                    "update_time": now
                }},
                upsert=True
            ))
        if len(opt) != 0:
            await self.mongo.db.user_detail_cache.bulk_write(opt, ordered=False)

    def user_illusts(self, user_id: int, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("user_illusts_cache", "user_id", user_id, skip=skip, limit=limit)()

    def update_user_illusts(self, user_id: int, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("user_illusts_cache", "user_id", user_id)(content)

    def user_bookmarks(self, user_id: int, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("user_bookmarks_cache", "user_id", user_id, skip=skip, limit=limit)()

    def update_user_bookmarks(self, user_id: int, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("user_bookmarks_cache", "user_id", user_id)(content)

    def recommended_illusts(self, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("other_cache", "type", "recommended_illusts", skip=skip, limit=limit)()

    def update_recommended_illusts(self, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("other_cache", "type", "recommended_illusts")(content)

    def related_illusts(self, illust_id: int, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("related_illusts_cache", "original_illust_id", illust_id, skip=skip,
                                               limit=limit)()

    def update_related_illusts(self, illust_id: int, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("related_illusts_cache", "original_illust_id", illust_id)(content)

    def illust_ranking(self, mode: RankingMode = RankingMode.day, *, skip: int = 0, limit: int = 0):
        return self._make_illusts_cache_loader("other_cache", "type", mode.name + "_ranking", skip=skip, limit=limit)()

    def update_illust_ranking(self, mode: RankingMode, content: typing.List[typing.Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("other_cache", "type", mode.name + "_ranking")(content)

    async def image(self, illust: Illust) -> typing.Optional[bytes]:
        cache = await self.mongo.db.download_cache.find_one({"illust_id": illust.id})
        if cache is not None:
            return cache["content"]
        else:
            return None

    async def update_image(self, illust: Illust, content: bytes):
        now = datetime.now()
        await self.mongo.db.download_cache.update_one(
            {"illust_id": illust.id},
            {"$set": {
                "content": bson.Binary(content),
                "update_time": now
            }},
            upsert=True
        )

    async def invalidate_cache(self):
        await self.mongo.db.download_cache.delete_many({})
        await self.mongo.db.illust_detail_cache.delete_many({})
        await self.mongo.db.user_detail_cache.delete_many({})
        await self.mongo.db.illust_ranking_cache.delete_many({})
        await self.mongo.db.search_illust_cache.delete_many({})
        await self.mongo.db.search_user_cache.delete_many({})
        await self.mongo.db.user_illusts_cache.delete_many({})
        await self.mongo.db.user_bookmarks_cache.delete_many({})
        await self.mongo.db.other_cache.delete_many({})

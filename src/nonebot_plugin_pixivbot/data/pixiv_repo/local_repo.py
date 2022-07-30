from datetime import datetime
from typing import Optional, List, Any, Union, Tuple

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

    def _make_illusts_cache_loader(self, collection_name: str, arg_name: str, arg: Any, *, skip: int = 0,
                                   limit: int = 0):
        async def cache_loader() -> Optional[List[LazyIllust]]:
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

            logger.info(f"[local] {len(cache)} got, illust_detail of {broken} are missed")

            if len(cache) != 0:
                return cache
            else:
                return None

        return cache_loader

    def _make_illusts_cache_updater(self, collection_name: str,
                                    arg_name: str,
                                    arg: Any):
        async def cache_updater(content: List[Union[Illust, LazyIllust]]):
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

    async def illust_detail(self, illust_id: int) -> Optional[Illust]:
        logger.info(f"[local] illust_detail {illust_id}")
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

    async def user_detail(self, user_id: int) -> Optional[User]:
        logger.info(f"[local] user_detail {user_id}")
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

    def search_illust(self, word: str):
        logger.info(f"[local] search_illust {word}")
        return self._make_illusts_cache_loader("search_illust_cache", "word", word)()

    def update_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("search_illust_cache", "word", word)(content)

    async def search_user(self, word: str) -> Optional[List[User]]:
        logger.info(f"[local] search_user {word}")
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

    async def update_search_user(self, word: str, content: List[User]):
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

    def user_illusts(self, user_id: int):
        logger.info(f"[local] user_illusts {user_id}")
        return self._make_illusts_cache_loader("user_illusts_cache", "user_id", user_id)()

    def update_user_illusts(self, user_id: int, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("user_illusts_cache", "user_id", user_id)(content)

    def user_bookmarks(self, user_id: int):
        logger.info(f"[local] user_bookmarks {user_id}")
        return self._make_illusts_cache_loader("user_bookmarks_cache", "user_id", user_id)()

    def update_user_bookmarks(self, user_id: int, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("user_bookmarks_cache", "user_id", user_id)(content)

    def recommended_illusts(self):
        logger.info(f"[local] recommended_illusts")
        return self._make_illusts_cache_loader("other_cache", "type", "recommended_illusts")()

    def update_recommended_illusts(self, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("other_cache", "type", "recommended_illusts")(content)

    def related_illusts(self, illust_id: int):
        logger.info(f"[local] related_illusts {illust_id}")
        return self._make_illusts_cache_loader("related_illusts_cache", "original_illust_id", illust_id)()

    def update_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("related_illusts_cache", "original_illust_id", illust_id)(content)

    def illust_ranking(self, mode: RankingMode = RankingMode.day,
                       *, range: Tuple[int, int]):
        logger.info(f"[local] illust_ranking {mode}")
        return self._make_illusts_cache_loader("other_cache", "type", mode.name + "_ranking", skip=range[0] - 1,
                                               limit=range[1] - range[0] + 1)()

    def update_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]]):
        return self._make_illusts_cache_updater("other_cache", "type", mode.name + "_ranking")(content)

    async def image(self, illust: Illust) -> Optional[bytes]:
        logger.info(f"[local] image {illust.id}")
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

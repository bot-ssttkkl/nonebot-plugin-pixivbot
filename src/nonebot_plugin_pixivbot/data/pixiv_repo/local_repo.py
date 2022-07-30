from datetime import datetime
from typing import Optional, List, Any, Union, Tuple, AsyncGenerator

import bson
from nonebot import logger
from pymongo import UpdateOne

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo, NoSuchItemError
from .lazy_illust import LazyIllust
from .pkg_context import context
from ..source import MongoDataSource


@context.register_singleton()
class LocalPixivRepo(AbstractPixivRepo):
    def __init__(self):
        self.mongo = context.require(MongoDataSource)

    async def _illusts_agen(self, collection_name: str, arg_name: str, arg: Any,
                            *, skip: int = 0, limit: int = 0, tag: str = 0) -> AsyncGenerator[LazyIllust, None]:
        exists = await self.mongo.db[collection_name].count_documents({arg_name: arg})
        if not exists:
            raise NoSuchItemError()

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

        total = 0
        broken = 0

        try:
            async for x in result:
                total += 1
                if "illust" in x and x["illust"] is not None:
                    yield LazyIllust(x["illust_id"], Illust.parse_obj(x["illust"]))
                else:
                    yield LazyIllust(x["illust_id"])
                    broken += 1
        finally:
            logger.info(f"[local] {total} got, illust_detail of {broken} are missed")

    async def _update_illusts(self, collection_name: str,
                              arg_name: str,
                              arg: Any,
                              content: List[Union[Illust, LazyIllust]]):
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

    async def illust_detail(self, illust_id: int) -> Optional[Illust]:
        logger.info(f"[local] illust_detail {illust_id}")
        cache = await self.mongo.db.illust_detail_cache.find_one({"illust.id": illust_id})
        if cache is not None:
            return Illust.parse_obj(cache["illust"])
        else:
            return None

    async def update_illust_detail(self, illust: Illust):
        logger.info(f"[local] update illust_detail {illust.id}")
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
        logger.info(f"[local] update user_detail {user.id}")
        await self.mongo.db.user_detail_cache.update_one(
            {"user.id": user.id},
            {"$set": {
                "user": user.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[local] search_illust {word}")
        async for x in self._illusts_agen("search_illust_cache", "word", word):
            yield x

    async def update_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update search_illust {word}")
        await self._update_illusts("search_illust_cache", "word", word, content)

    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.info(f"[local] search_user {word}")

        exists = await self.mongo.db.search_user_cache.find({"word": word}).count(True)
        if not exists:
            raise NoSuchItemError()

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

        async for x in result:
            if "user" in x and x["user"] is not None:
                yield User.parse_obj(x["user"])
            else:
                yield User(id=x["user_id"], name="", account="")

    async def update_search_user(self, word: str, content: List[User]):
        logger.info(f"[local] update search_user {word}")

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

    async def user_illusts(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[local] user_illusts {user_id}")
        async for x in self._illusts_agen("user_illusts_cache", "user_id", user_id):
            yield x

    async def update_user_illusts(self, user_id: int, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update user_illusts {user_id}")
        await self._update_illusts("user_illusts_cache", "user_id", user_id, content)

    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[local] user_bookmarks {user_id}")
        async for x in self._illusts_agen("user_bookmarks_cache", "user_id", user_id):
            yield x

    async def update_user_bookmarks(self, user_id: int, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update user_bookmarks {user_id}")
        await self._update_illusts("user_bookmarks_cache", "user_id", user_id, content)

    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[local] recommended_illusts")
        async for x in self._illusts_agen("other_cache", "type", "recommended_illusts"):
            yield x

    async def update_recommended_illusts(self, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update recommended_illusts")
        await self._update_illusts("other_cache", "type", "recommended_illusts", content)

    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[local] related_illusts {illust_id}")
        async for x in self._illusts_agen("related_illusts_cache", "original_illust_id", illust_id):
            yield x

    async def update_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update related_illusts {illust_id}")
        await self._update_illusts("related_illusts_cache", "original_illust_id", illust_id, content)

    async def illust_ranking(self, mode: RankingMode, range: Optional[Tuple[int, int]] = None) -> List[LazyIllust]:
        if range:
            logger.info(f"[local] illust_ranking {mode} {range[0]}-{range[1]}")
            gen = self._illusts_agen("other_cache", "type",
                                     mode.name + "_ranking",
                                     skip=range[0] - 1,
                                     limit=range[1] - range[0] + 1)
        else:
            raise ValueError("range cannot be None")
        return [x async for x in gen]

    async def update_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]]):
        logger.info(f"[local] update illust_ranking {mode}")
        await self._update_illusts("other_cache", "type", mode.name + "_ranking", content)

    async def image(self, illust: Illust) -> Optional[bytes]:
        logger.info(f"[local] image {illust.id}")
        cache = await self.mongo.db.download_cache.find_one({"illust_id": illust.id})
        if cache is not None:
            return cache["content"]
        else:
            return None

    async def update_image(self, illust: Illust, content: bytes):
        logger.info(f"[local] update image {illust.id}")
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
        logger.info(f"[local] invalidate_cache")
        await self.mongo.db.download_cache.delete_many({})
        await self.mongo.db.illust_detail_cache.delete_many({})
        await self.mongo.db.user_detail_cache.delete_many({})
        await self.mongo.db.illust_ranking_cache.delete_many({})
        await self.mongo.db.search_illust_cache.delete_many({})
        await self.mongo.db.search_user_cache.delete_many({})
        await self.mongo.db.user_illusts_cache.delete_many({})
        await self.mongo.db.user_bookmarks_cache.delete_many({})
        await self.mongo.db.other_cache.delete_many({})

from datetime import datetime, timedelta
from typing import Optional, List, Union, Tuple, AsyncGenerator, Sequence

import bson
from nonebot import logger
from pymongo import UpdateOne

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo
from .lazy_illust import LazyIllust
from .pkg_context import context
from ..source import MongoDataSource
from ...config import Config


class LocalPixivRepoError(RuntimeError):
    pass


class NoSuchItemError(LocalPixivRepoError):
    pass


class CacheExpiredError(LocalPixivRepoError):
    pass


def is_expired(update_time: datetime, expired_in: int):
    return datetime.now() - update_time >= timedelta(expired_in)


@context.inject
@context.register_singleton()
class LocalPixivRepo(AbstractPixivRepo):
    conf: Config
    mongo: MongoDataSource

    async def _illusts_agen(self, collection_name: str,
                            query: dict,
                            expired_in: int,
                            *, skip: int = 0, limit: int = 0) -> AsyncGenerator[LazyIllust, None]:
        update_time_result = await self.mongo.db[collection_name].find_one(query, {"update_time": 1})
        if not update_time_result:
            raise NoSuchItemError()
        elif is_expired(update_time_result["update_time"], expired_in):
            raise CacheExpiredError()

        aggregation = [
            {
                "$match": query
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
            logger.debug(f"[local] {total} got, illust_detail of {broken} are missed")

    async def _check_illusts_exists(self, collection_name: str,
                                    query: dict,
                                    illust_id: Union[int, Sequence[int]]):
        if isinstance(illust_id, int):
            return await self.mongo.db[collection_name].count_documents({**query, "illust_id": illust_id}) != 0
        else:
            agg = [
                {'$match': query},
                {'$unwind': {'path': '$illust_id'}},
                {'$match': {'illust_id': {'$in': illust_id}}},
                {'$count': 'count'}
            ]

            async for x in self.mongo.db[collection_name].aggregate(agg):
                exists = x["count"]
                return exists != 0

    async def _update_illusts(self, collection_name: str,
                              query: dict,
                              content: List[Union[Illust, LazyIllust]],
                              append: bool = False):
        now = datetime.now()
        if append:
            await self.mongo.db[collection_name].update_one(
                query,
                {
                    "$set": {
                        "update_time": now
                    },
                    "$addToSet": {
                        "illust_id": {
                            "$each": [illust.id for illust in content]
                        }
                    }
                },
                upsert=True
            )
        else:
            await self.mongo.db[collection_name].update_one(
                query,
                {
                    "$set": {
                        "illust_id": [illust.id for illust in content],
                        "update_time": now
                    }
                },
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

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) -> Optional[Illust]:
        logger.debug(f"[local] illust_detail {illust_id}")
        cache = await self.mongo.db.illust_detail_cache.find_one({"illust.id": illust_id})
        if cache is not None:
            return Illust.parse_obj(cache["illust"])
        elif is_expired(cache["update_time"], self.conf.pixiv_illust_detail_cache_expires_in):
            raise CacheExpiredError()
        else:
            raise NoSuchItemError()

    async def update_illust_detail(self, illust: Illust):
        logger.debug(f"[local] update illust_detail {illust.id}")
        await self.mongo.db.illust_detail_cache.update_one(
            {"illust.id": illust.id},
            {"$set": {
                "illust": illust.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    # ================ user_detail ================
    async def user_detail(self, user_id: int) -> Optional[User]:
        logger.debug(f"[local] user_detail {user_id}")
        cache = await self.mongo.db.user_detail_cache.find_one({"user.id": user_id})
        if cache is not None:
            return User.parse_obj(cache["user"])
        elif is_expired(cache["update_time"], self.conf.pixiv_user_detail_cache_expires_in):
            raise CacheExpiredError()
        else:
            raise NoSuchItemError()

    async def update_user_detail(self, user: User):
        logger.debug(f"[local] update user_detail {user.id}")
        await self.mongo.db.user_detail_cache.update_one(
            {"user.id": user.id},
            {"$set": {
                "user": user.dict(),
                "update_time": datetime.now()
            }},
            upsert=True
        )

    # ================ search_illust ================
    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[local] search_illust {word}")
        async for x in self._illusts_agen("search_illust_cache", {"word": word},
                                          self.conf.pixiv_search_illust_cache_expires_in):
            yield x

    async def update_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update search_illust {word} ({len(content)} illusts)")
        await self._update_illusts("search_illust_cache", {"word": word}, content)

    # ================ search_user ================
    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.debug(f"[local] search_user {word}")

        update_time_result = await self.mongo.db["search_user_cache"].find_one({"word": word}, {"update_time": 1})
        if not update_time_result:
            raise NoSuchItemError()
        elif is_expired(update_time_result["update_time"], self.conf.pixiv_search_user_cache_expires_in):
            raise CacheExpiredError()

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
        logger.debug(f"[local] update search_user {word} ({len(content)} illusts)")

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

    # ================ user_illusts ================
    async def user_illusts(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[local] user_illusts {user_id}")
        async for x in self._illusts_agen("user_illusts_cache", {"user_id": user_id},
                                          self.conf.pixiv_user_illusts_cache_expires_in):
            yield x

    async def update_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update user_illusts {user_id} ({len(content)} illusts)")
        await self._update_illusts("user_illusts_cache", {"user_id": user_id}, content)

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]]) -> bool:
        logger.debug(f"[local] append user_illusts {user_id} ({len(content)} illusts)")
        exists = await self._check_illusts_exists("user_illusts_cache", {"user_id": user_id}, [x.id for x in content])
        await self._update_illusts("user_illusts_cache", {"user_id": user_id}, content, True)
        return exists

    # ================ user_bookmarks ================
    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[local] user_bookmarks {user_id}")
        async for x in self._illusts_agen("user_bookmarks_cache", {"user_id": user_id},
                                          self.conf.pixiv_user_bookmarks_cache_expires_in):
            yield x

    async def update_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update user_bookmarks {user_id} ({len(content)} illusts)")
        await self._update_illusts("user_bookmarks_cache", {"user_id": user_id}, content)

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]]) -> bool:
        logger.debug(f"[local] append user_bookmarks {user_id} ({len(content)} illusts)")
        exists = await self._check_illusts_exists("user_bookmarks_cache", {"user_id": user_id}, [x.id for x in content])
        await self._update_illusts("user_bookmarks_cache", {"user_id": user_id}, content, True)
        return exists

    # ================ recommended_illusts ================
    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[local] recommended_illusts")
        async for x in self._illusts_agen("other_cache", {"type": "recommended_illusts"},
                                          self.conf.pixiv_other_cache_expires_in):
            yield x

    async def update_recommended_illusts(self, content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update recommended_illusts ({len(content)} illusts)")
        await self._update_illusts("other_cache", {"type": "recommended_illusts"}, content)

    # ================ related_illusts ================
    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[local] related_illusts {illust_id}")
        async for x in self._illusts_agen("related_illusts_cache", {"original_illust_id": illust_id},
                                          self.conf.pixiv_related_illusts_cache_expires_in):
            yield x

    async def update_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update related_illusts {illust_id} ({len(content)} illusts)")
        await self._update_illusts("related_illusts_cache", {"original_illust_id": illust_id}, content)

    # ================ illust_ranking ================
    async def illust_ranking(self, mode: RankingMode, range: Optional[Tuple[int, int]]) -> List[LazyIllust]:
        logger.debug(f"[local] illust_ranking {mode} {range[0]}~{range[1]}")
        gen = self._illusts_agen("other_cache", {"type": mode.name + "_ranking"},
                                 self.conf.pixiv_illust_ranking_cache_expires_in,
                                 skip=range[0] - 1,
                                 limit=range[1] - range[0] + 1)
        return [x async for x in gen]

    async def update_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]]):
        logger.debug(f"[local] update illust_ranking {mode} ({len(content)} illusts)")
        await self._update_illusts("other_cache", {"type": mode.name + "_ranking"}, content)

    # ================ image ================
    async def image(self, illust: Illust) -> Optional[bytes]:
        logger.debug(f"[local] image {illust.id}")
        cache = await self.mongo.db.download_cache.find_one({"illust_id": illust.id})
        if cache is not None:
            return cache["content"]
        elif is_expired(cache["update_time"], self.conf.pixiv_download_cache_expires_in):
            raise CacheExpiredError()
        else:
            raise NoSuchItemError()

    async def update_image(self, illust_id: int, content: bytes):
        logger.debug(f"[local] update image {illust_id}")
        now = datetime.now()
        await self.mongo.db.download_cache.update_one(
            {"illust_id": illust_id},
            {"$set": {
                "content": bson.Binary(content),
                "update_time": now
            }},
            upsert=True
        )

    async def invalidate_cache(self):
        logger.debug(f"[local] invalidate_cache")
        await self.mongo.db.download_cache.delete_many({})
        await self.mongo.db.illust_detail_cache.delete_many({})
        await self.mongo.db.user_detail_cache.delete_many({})
        await self.mongo.db.illust_ranking_cache.delete_many({})
        await self.mongo.db.search_illust_cache.delete_many({})
        await self.mongo.db.search_user_cache.delete_many({})
        await self.mongo.db.user_illusts_cache.delete_many({})
        await self.mongo.db.user_bookmarks_cache.delete_many({})
        await self.mongo.db.other_cache.delete_many({})

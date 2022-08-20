from datetime import datetime, timedelta, timezone
from typing import List, Union, Sequence, Any, Mapping, AsyncGenerator

import bson
from nonebot import logger
from pymongo import UpdateOne

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo, PixivRepoMetadata
from .lazy_illust import LazyIllust
from .pkg_context import context
from ..local_tag_repo import LocalTagRepo
from ..source import MongoDataSource
from ...config import Config


class LocalPixivRepoError(RuntimeError):
    pass


class NoSuchItemError(LocalPixivRepoError):
    pass


class CacheExpiredError(LocalPixivRepoError):
    def __init__(self, metadata: PixivRepoMetadata):
        self.metadata = metadata


def handle_expires_in(doc: Mapping, expires_in: int):
    if datetime.now(timezone.utc) - doc["metadata"]["update_time"] >= timedelta(seconds=expires_in):
        raise CacheExpiredError(PixivRepoMetadata.parse_obj(doc["metadata"]))


def metadata_to_text(metadata: PixivRepoMetadata):
    if metadata:
        return '(' + ', '.join(map(lambda kv: kv[0] + '=' + str(kv[1]), metadata.dict(exclude_none=True).items())) + ')'
    else:
        return ''


@context.inject
@context.register_singleton()
class LocalPixivRepo(AbstractPixivRepo):
    conf: Config
    mongo: MongoDataSource
    local_tags: LocalTagRepo

    async def _add_to_local_tags(self, illusts: List[Union[LazyIllust, Illust]]):
        tags = {}
        for x in illusts:
            if isinstance(x, LazyIllust):
                if not x.loaded:
                    continue
                x = x.content
            for t in x.tags:
                if t.translated_name:
                    tags[t.name] = t

        await self.local_tags.insert_many(tags.values())
        logger.debug(f"[local] add {len(tags)} local tags")

    async def _illusts_agen(self, collection_name: str,
                            query: dict,
                            *, offset: int = 0) -> AsyncGenerator[LazyIllust, None]:
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

        if offset:
            aggregation.append({"$offset": offset})

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

    async def _users_agen(self, collection_name: str,
                          query: dict,
                          *, offset: int = 0) -> AsyncGenerator[User, None]:
        aggregation = [
            {
                "$match": query
            },
            {
                "$replaceWith": {"user_id": "$user_id"}
            },
            {
                "$unwind": "$user_id"
            },
        ]

        if offset:
            aggregation.append({"$offset": offset})

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

        result = self.mongo.db[collection_name].aggregate(aggregation)

        async for x in result:
            if "user" in x and x["user"] is not None:
                yield User.parse_obj(x["user"])
            else:
                yield User(id=x["user_id"], name="", account="")

    async def _get_illusts(self, collection_name: str,
                           query: dict,
                           *, expired_in: int,
                           offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], Any]:
        doc = await self.mongo.db[collection_name].find_one(query, {"metadata": 1})
        if not doc:
            raise NoSuchItemError()
        handle_expires_in(doc, expired_in)

        metadata = PixivRepoMetadata.parse_obj(doc["metadata"])
        yield metadata.copy(update={"pages": 0})
        async for x in self._illusts_agen(collection_name, query, offset=offset):
            yield x
        yield metadata

    async def _get_users(self, collection_name: str,
                         query: dict,
                         *, expired_in: int,
                         offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], Any]:
        doc = await self.mongo.db[collection_name].find_one(query, {"metadata": 1})
        if not doc:
            raise NoSuchItemError()
        handle_expires_in(doc, expired_in)

        metadata = PixivRepoMetadata.parse_obj(doc["metadata"])
        yield metadata.copy(update={"pages": 0})
        async for x in self._users_agen(collection_name, query, offset=offset):
            yield x
        yield metadata

    async def _check_illusts_exists(self, collection_name: str,
                                    query: dict,
                                    illust_id: Union[int, Sequence[int]]) -> bool:
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

    async def _check_users_exists(self, collection_name: str,
                                  query: dict,
                                  user_id: Union[int, Sequence[int]]) -> bool:
        if isinstance(user_id, int):
            return await self.mongo.db[collection_name].count_documents({**query, "user_id": user_id}) != 0
        else:
            agg = [
                {'$match': query},
                {'$unwind': {'path': '$user_id'}},
                {'$match': {'user_id': {'$in': user_id}}},
                {'$count': 'count'}
            ]

            async for x in self.mongo.db[collection_name].aggregate(agg):
                exists = x["count"]
                return exists != 0

    async def _update_illusts(self, collection_name: str,
                              query: dict,
                              content: List[Union[Illust, LazyIllust]],
                              metadata: PixivRepoMetadata,
                              append: bool = False):
        if append:
            await self.mongo.db[collection_name].update_one(
                query,
                {
                    "$set": {
                        "metadata": metadata.dict(exclude_none=True)
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
                        "metadata": metadata.dict(exclude_none=True)
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
                        "illust": illust.dict(exclude_none=True),
                        "metadata": {"update_time": metadata.update_time}
                    }},
                    upsert=True
                ))
        if len(opt) != 0:
            await self.mongo.db.illust_detail_cache.bulk_write(opt, ordered=False)

        if self.conf.pixiv_tag_translation_enabled:
            await self._add_to_local_tags(content)

    async def _update_users(self, collection_name: str,
                            query: dict,
                            content: List[User],
                            metadata: PixivRepoMetadata,
                            append: bool = False):
        if append:
            await self.mongo.db[collection_name].update_one(
                query,
                {
                    "$set": {
                        "metadata": metadata.dict(exclude_none=True)
                    },
                    "$addToSet": {
                        "user_id": {
                            "$each": [user.id for user in content]
                        }
                    }
                },
                upsert=True
            )
        else:
            await self.mongo.db[collection_name].update_one(
                query,
                {"$set": {
                    "user_id": [user.id for user in content],
                    "metadata": metadata.dict(exclude_none=True)
                }},
                upsert=True
            )

        opt = []
        for user in content:
            opt.append(UpdateOne(
                {"user.id": user.id},
                {"$set": {
                    "user": user.dict(exclude_none=True),
                    "metadata": {"update_time": metadata.update_time}
                }},
                upsert=True
            ))
        if len(opt) != 0:
            await self.mongo.db.user_detail_cache.bulk_write(opt, ordered=False)

    async def _append_and_check_illusts(self, collection_name: str,
                                        query: dict,
                                        content: List[Union[Illust, LazyIllust]],
                                        metadata: PixivRepoMetadata):
        exists = await self._check_illusts_exists(collection_name, query, [x.id for x in content])
        await self._update_illusts(collection_name, query, content, metadata, True)
        return exists

    async def _append_and_check_users(self, collection_name: str,
                                      query: dict,
                                      content: List[User],
                                      metadata: PixivRepoMetadata):
        exists = await self._check_users_exists(collection_name, query, [x.id for x in content])
        await self._update_users(collection_name, query, content, metadata, True)
        return exists

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) \
            -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        logger.debug(f"[local] illust_detail {illust_id}")
        doc = await self.mongo.db.illust_detail_cache.find_one({"illust.id": illust_id})
        if doc is not None:
            handle_expires_in(doc, self.conf.pixiv_illust_detail_cache_expires_in)

            yield PixivRepoMetadata.parse_obj(doc["metadata"])
            yield Illust.parse_obj(doc["illust"])
        else:
            raise NoSuchItemError()

    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata = PixivRepoMetadata()):
        logger.debug(f"[local] update illust_detail {illust.id} {metadata_to_text(metadata)}")

        await self.mongo.db.illust_detail_cache.update_one(
            {"illust.id": illust.id},
            {"$set": {
                "illust": illust.dict(exclude_none=True),
                "metadata": metadata.dict(exclude_none=True)
            }},
            upsert=True
        )

        if self.conf.pixiv_tag_translation_enabled:
            await self._add_to_local_tags([illust])

    # ================ user_detail ================
    async def user_detail(self, user_id: int) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_detail {user_id}")
        doc = await self.mongo.db.user_detail_cache.find_one({"user.id": user_id})
        if doc is not None:
            handle_expires_in(doc, self.conf.pixiv_user_detail_cache_expires_in)

            yield PixivRepoMetadata.parse_obj(doc["metadata"])
            yield User.parse_obj(doc["user"])
        else:
            raise NoSuchItemError()

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata = PixivRepoMetadata()):
        logger.debug(f"[local] update user_detail {user.id} {metadata_to_text(metadata)}")

        if not metadata:
            metadata = PixivRepoMetadata(update_time=datetime.now(timezone.utc))

        await self.mongo.db.user_detail_cache.update_one(
            {"user.id": user.id},
            {"$set": {
                "user": user.dict(exclude_none=True),
                "metadata": metadata.dict(exclude_none=True)
            }},
            upsert=True
        )

    # ================ search_illust ================
    def search_illust(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_illust {word}")
        return self._get_illusts("search_illust_cache", {"word": word},
                                 expired_in=self.conf.pixiv_search_illust_cache_expires_in,
                                 offset=offset)

    async def update_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata):
        logger.debug(f"[local] update search_illust {word} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("search_illust_cache", {"word": word}, content, metadata)

    async def append_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append search_illust {word} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("search_illust_cache", {"word": word}, content, metadata)

    # ================ search_user ================
    def search_user(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_user {word}")
        return self._get_users("search_user_cache", {"word": word},
                               expired_in=self.conf.pixiv_search_user_cache_expires_in,
                               offset=offset)

    async def update_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata):
        logger.debug(f"[local] update search_user {word} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_users("search_user_cache", {"word": word}, content, metadata)

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append search_user {word} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_users("search_user_cache", {"word": word}, content, metadata)

    # ================ user_illusts ================
    def user_illusts(self, user_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_illusts {user_id}")
        return self._get_illusts("user_illusts_cache", {"user_id": user_id},
                                 expired_in=self.conf.pixiv_user_illusts_cache_expires_in,
                                 offset=offset)

    async def update_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata):
        logger.debug(f"[local] update user_illusts {user_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("user_illusts_cache", {"user_id": user_id}, content, metadata)

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append user_illusts {user_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("user_illusts_cache", {"user_id": user_id}, content, metadata)

    # ================ user_bookmarks ================
    def user_bookmarks(self, user_id: int = 0, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_bookmarks {user_id}")
        return self._get_illusts("user_bookmarks_cache", {"user_id": user_id},
                                 expired_in=self.conf.pixiv_user_bookmarks_cache_expires_in,
                                 offset=offset)

    async def update_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata):
        logger.debug(f"[local] update user_bookmarks {user_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("user_bookmarks_cache", {"user_id": user_id}, content, metadata)

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append user_bookmarks {user_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("user_bookmarks_cache", {"user_id": user_id}, content, metadata)

    # ================ recommended_illusts ================
    def recommended_illusts(self, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] recommended_illusts")
        return self._get_illusts("other_cache", {"type": "recommended_illusts"},
                                 expired_in=self.conf.pixiv_other_cache_expires_in,
                                 offset=offset)

    async def update_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata):
        logger.debug(f"[local] update recommended_illusts "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("other_cache", {"type": "recommended_illusts"}, content, metadata)

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append recommended_illusts "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("other_cache", {"type": "recommended_illusts"}, content, metadata)

    # ================ related_illusts ================
    def related_illusts(self, illust_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] related_illusts {illust_id}")
        return self._get_illusts("related_illusts_cache", {"original_illust_id": illust_id},
                                 expired_in=self.conf.pixiv_related_illusts_cache_expires_in,
                                 offset=offset)

    async def update_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata):
        logger.debug(f"[local] update related_illusts {illust_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("related_illusts_cache", {"original_illust_id": illust_id}, content, metadata)

    async def append_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append related_illusts {illust_id} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("related_illusts_cache", {"original_illust_id": illust_id}, content,
                                                    metadata)

    # ================ illust_ranking ================
    def illust_ranking(self, mode: Union[str, RankingMode], *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.debug(f"[local] illust_ranking {mode}")

        return self._get_illusts("other_cache", {"type": mode.name + "_ranking"},
                                 expired_in=self.conf.pixiv_illust_ranking_cache_expires_in,
                                 offset=offset)

    async def update_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata):
        logger.debug(f"[local] update illust_ranking {mode} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        await self._update_illusts("other_cache", {"type": mode.name + "_ranking"}, content, metadata)

    async def append_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append illust_ranking {mode} "
                     f"({len(content)} items) "
                     f"{metadata_to_text(metadata)}")
        return await self._append_and_check_illusts("other_cache", {"type": mode.name + "_ranking"}, content, metadata)

    # ================ image ================
    async def image(self, illust: Illust) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        logger.debug(f"[local] image {illust.id}")
        doc = await self.mongo.db.download_cache.find_one({"illust_id": illust.id})
        if doc is not None:
            handle_expires_in(doc, self.conf.pixiv_download_cache_expires_in)
            yield PixivRepoMetadata.parse_obj(doc["metadata"])
            yield doc["content"]
        else:
            raise NoSuchItemError()

    async def update_image(self, illust_id: int, content: bytes,
                           metadata: PixivRepoMetadata = PixivRepoMetadata()):
        logger.debug(f"[local] update image {illust_id} "
                     f"{metadata_to_text(metadata)}")

        await self.mongo.db.download_cache.update_one(
            {"illust_id": illust_id},
            {"$set": {
                "content": bson.Binary(content),
                "metadata": metadata.dict(exclude_none=True)
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

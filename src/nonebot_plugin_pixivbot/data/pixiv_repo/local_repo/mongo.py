from datetime import datetime, timedelta, timezone
from typing import List, Union, Sequence, Any, AsyncGenerator, Optional, Type, Mapping

import bson
from beanie.odm.operators.find.comparison import In
from beanie.odm.operators.find.logical import And
from beanie.odm.operators.update.array import AddToSet
from beanie.odm.operators.update.general import Set
from nonebot import logger
from pymongo import UpdateOne

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .mongo_models import UserDetailCache, PixivRepoCache, IllustDetailCache, IllustSetCache, UserSetCache, \
    SearchIllustCache, SearchUserCache, UserIllustsCache, UserBookmarksCache, OtherIllustCache, RelatedIllustsCache, \
    IllustRankingCache, DownloadCache
from ..errors import CacheExpiredError, NoSuchItemError
from ..lazy_illust import LazyIllust
from ..models import PixivRepoMetadata
from ...local_tag import LocalTagRepo
from ...source.mongo import MongoDataSource


def _handle_expires_in(metadata: PixivRepoMetadata, expires_in: int):
    if datetime.now(timezone.utc) - metadata.update_time >= timedelta(seconds=expires_in):
        raise CacheExpiredError(metadata)


@context.inject
@context.register_singleton()
class MongoPixivRepo:
    conf: Config = Inject(Config)
    mongo: MongoDataSource = Inject(MongoDataSource)
    local_tag_repo: LocalTagRepo = Inject(LocalTagRepo)

    async def _add_to_local_tags(self, illusts: List[Union[LazyIllust, Illust]]):
        li = []
        for x in illusts:
            if isinstance(x, LazyIllust):
                if not x.loaded:
                    continue
                x = x.content
            li.append(x)

        await self.local_tag_repo.update_from_illusts(li)

    async def _illusts_agen(self, doc_type: Type[PixivRepoCache],
                            *criteria: Union[Mapping[str, Any], bool],
                            offset: int = 0) -> AsyncGenerator[LazyIllust, None]:
        aggregation = [
            {
                "$match": And(*criteria).query
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
                    "from": IllustDetailCache.Settings.name,
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

        total = 0
        broken = 0

        try:
            # noinspection PyTypeChecker
            async for x in doc_type.aggregate(aggregation, session=self.mongo.session()):
                total += 1
                if "illust" in x and x["illust"] is not None:
                    yield LazyIllust(x["illust_id"], Illust.parse_obj(x["illust"]))
                else:
                    yield LazyIllust(x["illust_id"])
                    broken += 1
        finally:
            logger.info(f"[local] got {total} illusts, illust_detail of {broken} are missed")

    async def _users_agen(self, doc_type: Type[PixivRepoCache],
                          *criteria: Union[Mapping[str, Any], bool],
                          offset: int = 0) -> AsyncGenerator[User, None]:
        aggregation = [
            {
                "$match": And(*criteria).query
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
                    "from": UserDetailCache.Settings.name,
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

        total = 0
        try:
            # noinspection PyTypeChecker
            async for x in doc_type.aggregate(aggregation, session=self.mongo.session()):
                if "user" in x and x["user"] is not None:
                    yield User.parse_obj(x["user"])
                else:
                    yield User(id=x["user_id"], name="", account="")
                total += 1
        finally:
            logger.info(f"[local] got {total} users")

    async def _get_illusts(self, doc_type: Type[PixivRepoCache],
                           *criteria: Union[Mapping[str, Any], bool],
                           expired_in: int,
                           offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], Any]:
        doc: Optional[PixivRepoCache] = await doc_type.find_one(*criteria, session=self.mongo.session())
        if not doc:
            raise NoSuchItemError()
        _handle_expires_in(doc.metadata, expired_in)

        metadata = doc.metadata
        yield metadata.copy(update={"pages": 0})
        async for x in self._illusts_agen(doc_type, *criteria, offset=offset):
            yield x
        yield metadata

    async def _get_users(self, doc_type: Type[PixivRepoCache],
                         *criteria: Union[Mapping[str, Any], bool],
                         expired_in: int,
                         offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], Any]:
        doc: Optional[PixivRepoCache] = await doc_type.find_one(*criteria, session=self.mongo.session())
        if not doc:
            raise NoSuchItemError()
        _handle_expires_in(doc.metadata, expired_in)

        metadata = doc.metadata
        yield metadata.copy(update={"pages": 0})
        async for x in self._users_agen(doc_type, *criteria, offset=offset):
            yield x
        yield metadata

    async def _check_illusts_exists(self, doc_type: Type[IllustSetCache],
                                    *criteria: Union[Mapping[str, Any], bool],
                                    illust_id: Union[int, Sequence[int]]) -> bool:
        if isinstance(illust_id, int):
            return await doc_type.find(*criteria, In(doc_type.illust_id, illust_id),
                                       session=self.mongo.session()).count() != 0
        else:
            agg = [
                {'$match': And(*criteria).query},
                {'$unwind': {'path': '$illust_id'}},
                {'$match': {'illust_id': {'$in': illust_id}}},
                {'$count': 'count'}
            ]

            # noinspection PyTypeChecker
            async for result in doc_type.aggregate(agg):
                return result["count"] != 0

    async def _check_users_exists(self, doc_type: Type[UserSetCache],
                                  *criteria: Union[Mapping[str, Any], bool],
                                  user_id: Union[int, Sequence[int]]) -> bool:
        if isinstance(user_id, int):
            return await doc_type.find(*criteria, In(doc_type.user_id, user_id),
                                       session=self.mongo.session()).count() != 0
        else:
            agg = [
                {'$match': And(*criteria).query},
                {'$unwind': {'path': '$user_id'}},
                {'$match': {'user_id': {'$in': user_id}}},
                {'$count': 'count'}
            ]

            # noinspection PyTypeChecker
            async for result in doc_type.aggregate(agg, session=self.mongo.session()):
                return result["count"] != 0

    async def _update_illusts(self, doc_type: Type[IllustSetCache],
                              *criteria: Union[Mapping[str, Any], bool],
                              content: List[Union[Illust, LazyIllust]],
                              metadata: PixivRepoMetadata,
                              append: bool = False):
        if append:
            await doc_type.find_one(*criteria, session=self.mongo.session()).update(
                Set({
                    doc_type.metadata: metadata
                }),
                AddToSet({
                    doc_type.illust_id: {
                        "$each": [illust.id for illust in content]
                    }
                }),
                upsert=True,
                session=self.mongo.session()
            )
        else:
            await doc_type.find_one(*criteria, session=self.mongo.session()).update(
                Set({
                    doc_type.illust_id: [illust.id for illust in content],
                    doc_type.metadata: metadata
                }),
                upsert=True,
                session=self.mongo.session()
            )

        # BulkWriter存在bug，upsert不生效
        # https://github.com/roman-right/beanie/issues/224

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
            await IllustDetailCache.get_motor_collection().bulk_write(opt, ordered=False, session=self.mongo.session())

        if self.conf.pixiv_tag_translation_enabled:
            await self._add_to_local_tags(content)

    async def _update_users(self, doc_type: Type[UserSetCache],
                            *criteria: Union[Mapping[str, Any], bool],
                            content: List[User],
                            metadata: PixivRepoMetadata,
                            append: bool = False):
        if append:
            await doc_type.find_one(*criteria, session=self.mongo.session()).update(
                Set({
                    doc_type.metadata: metadata
                }),
                AddToSet({
                    doc_type.user_id: {
                        "$each": [user.id for user in content]
                    }
                }),
                upsert=True,
                session=self.mongo.session()
            )
        else:
            await doc_type.find_one(*criteria, session=self.mongo.session()).update(
                Set({
                    doc_type.user_id: [user.id for user in content],
                    doc_type.metadata: metadata
                }),
                upsert=True,
                session=self.mongo.session()
            )
        # BulkWriter存在bug，upsert不生效
        # https://github.com/roman-right/beanie/issues/224
        #
        # async with BulkWriter() as bw:
        #     user_metadata = PixivRepoMetadata(update_time=metadata.update_time)
        #
        #     for user in content:
        #         await UserDetailCache.find_one(
        #             UserDetailCache.user.id == user.id
        #         ).upsert(
        #             Set({
        #                 UserDetailCache.user: user,
        #                 UserDetailCache.metadata: user_metadata
        #             }),
        #             on_insert=UserDetailCache(user=user, metadata=user_metadata),
        #             bulk_writer=bw
        #         )

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
            await self.mongo.db.user_detail_cache.bulk_write(opt, ordered=False, session=self.mongo.session())

    async def _append_and_check_illusts(self, doc_type: Type[IllustSetCache],
                                        *criteria: Union[Mapping[str, Any], bool],
                                        content: List[Union[Illust, LazyIllust]],
                                        metadata: PixivRepoMetadata):
        exists = await self._check_illusts_exists(doc_type, *criteria, illust_id=[x.id for x in content])
        await self._update_illusts(doc_type, *criteria, content=content, metadata=metadata, append=True)
        return exists

    async def _append_and_check_users(self, doc_type: Type[UserSetCache],
                                      *criteria: Union[Mapping[str, Any], bool],
                                      content: List[User],
                                      metadata: PixivRepoMetadata):
        exists = await self._check_users_exists(doc_type, *criteria, user_id=[x.id for x in content])
        await self._update_users(doc_type, *criteria, content=content, metadata=metadata, append=True)
        return exists

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) \
            -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        logger.info(f"[local] illust_detail {illust_id}")
        doc = await IllustDetailCache.find_one(IllustDetailCache.illust.id == illust_id, session=self.mongo.session())
        if doc is not None:
            _handle_expires_in(doc.metadata, self.conf.pixiv_illust_detail_cache_expires_in)

            yield doc.metadata
            yield doc.illust
        else:
            raise NoSuchItemError()

    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata):
        logger.info(f"[local] update illust_detail {illust.id} {metadata}")

        await IllustDetailCache.find_one(
            IllustDetailCache.illust.id == illust.id,
            session=self.mongo.session()
        ).update(
            Set({
                IllustDetailCache.illust: illust,
                IllustDetailCache.metadata: metadata
            }),
            upsert=True,
            session=self.mongo.session()
        )

        if self.conf.pixiv_tag_translation_enabled:
            await self._add_to_local_tags([illust])

    # ================ user_detail ================
    async def user_detail(self, user_id: int) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.info(f"[local] user_detail {user_id}")
        doc: Optional[UserDetailCache] = await UserDetailCache.find_one(UserDetailCache.user.id == user_id,
                                                                        session=self.mongo.session())
        if doc is not None:
            _handle_expires_in(doc.metadata, self.conf.pixiv_user_detail_cache_expires_in)

            yield doc.metadata
            yield doc.user
        else:
            raise NoSuchItemError()

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata):
        logger.info(f"[local] update user_detail {user.id} {metadata}")

        if not metadata:
            metadata = PixivRepoMetadata(update_time=datetime.now(timezone.utc))

        await UserDetailCache.find_one(
            UserDetailCache.user.id == user.id,
            session=self.mongo.session()
        ).update(
            Set({
                UserDetailCache.user: user,
                UserDetailCache.metadata: metadata
            }),
            upsert=True,
            session=self.mongo.session()
        )

    # ================ search_illust ================
    def search_illust(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] search_illust {word}")
        return self._get_illusts(SearchIllustCache, SearchIllustCache.word == word,
                                 expired_in=self.conf.pixiv_search_illust_cache_expires_in, offset=offset)

    async def invalidate_search_illust(self, word: str):
        logger.info(f"[local] invalidate search_illust {word}")
        await self.mongo.db.search_illust_cache.delete_one({"word": word}, session=self.mongo.session())

    async def append_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        # 返回值表示content中是否有已经存在于集合的文档，下同
        logger.info(f"[local] append search_illust {word} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(SearchIllustCache, SearchIllustCache.word == word,
                                                    content=content, metadata=metadata)

    # ================ search_user ================

    def search_user(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.info(f"[local] search_user {word}")
        return self._get_users(SearchUserCache, SearchUserCache.word == word,
                               expired_in=self.conf.pixiv_search_user_cache_expires_in, offset=offset)

    async def invalidate_search_user(self, word: str):
        logger.info(f"[local] invalidate search_user {word}")
        await SearchUserCache.find_one(SearchUserCache.word == word, session=self.mongo.session()).delete()

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append search_user {word} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_users(SearchUserCache, SearchUserCache.word == word,
                                                  content=content, metadata=metadata)

    # ================ user_illusts ================

    def user_illusts(self, user_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] user_illusts {user_id}")
        return self._get_illusts(UserIllustsCache, UserIllustsCache.user_id == user_id,
                                 expired_in=self.conf.pixiv_user_illusts_cache_expires_in, offset=offset)

    async def invalidate_user_illusts(self, user_id: int):
        logger.info(f"[local] invalidate user_illusts {user_id}")
        await UserIllustsCache.find_one(UserIllustsCache.user_id == user_id, session=self.mongo.session()).delete()

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append user_illusts {user_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(UserIllustsCache, UserIllustsCache.user_id == user_id,
                                                    content=content, metadata=metadata)

    # ================ user_bookmarks ================

    def user_bookmarks(self, user_id: int = 0, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] user_bookmarks {user_id}")
        return self._get_illusts(UserBookmarksCache, UserBookmarksCache.user_id == user_id,
                                 expired_in=self.conf.pixiv_user_bookmarks_cache_expires_in, offset=offset)

    async def invalidate_user_bookmarks(self, user_id: int):
        logger.info(f"[local] invalidate user_bookmarks {user_id}")
        await UserBookmarksCache.find_one(UserBookmarksCache.user_id == user_id, session=self.mongo.session()).delete()

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append user_bookmarks {user_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(UserBookmarksCache, UserBookmarksCache.user_id == user_id,
                                                    content=content, metadata=metadata)

    # ================ recommended_illusts ================
    def recommended_illusts(self, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] recommended_illusts")
        return self._get_illusts(OtherIllustCache, OtherIllustCache.type == "recommended_illusts",
                                 expired_in=self.conf.pixiv_other_cache_expires_in, offset=offset)

    async def invalidate_recommended_illusts(self):
        logger.info(f"[local] invalidate recommended_illusts")
        await OtherIllustCache.find_one(OtherIllustCache.type == "recommended_illusts",
                                        session=self.mongo.session()).delete()

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append recommended_illusts "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(OtherIllustCache, OtherIllustCache.type == "recommended_illusts",
                                                    content=content, metadata=metadata)

    # ================ related_illusts ================

    def related_illusts(self, illust_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] related_illusts {illust_id}")
        return self._get_illusts(RelatedIllustsCache, RelatedIllustsCache.original_illust_id == illust_id,
                                 expired_in=self.conf.pixiv_related_illusts_cache_expires_in, offset=offset)

    async def invalidate_related_illusts(self, illust_id: int):
        logger.info(f"[local] invalidate related_illusts")
        await RelatedIllustsCache.find_one(RelatedIllustsCache.original_illust_id == illust_id,
                                           session=self.mongo.session()).delete()

    async def append_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append related_illusts {illust_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(RelatedIllustsCache,
                                                    RelatedIllustsCache.original_illust_id == illust_id,
                                                    content=content, metadata=metadata)

    # ================ illust_ranking ================
    def illust_ranking(self, mode: Union[str, RankingMode], *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.info(f"[local] illust_ranking {mode}")

        return self._get_illusts(IllustRankingCache, IllustRankingCache.mode == mode,
                                 expired_in=self.conf.pixiv_illust_ranking_cache_expires_in, offset=offset)

    async def invalidate_illust_ranking(self, mode: RankingMode):
        logger.info(f"[local] invalidate illust_ranking")
        await IllustRankingCache.find_one(IllustRankingCache.mode == mode,
                                          session=self.mongo.session()).delete()

    async def append_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append illust_ranking {mode} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts(IllustRankingCache, IllustRankingCache.mode == mode,
                                                    content=content, metadata=metadata)

    # ================ image ================
    async def image(self, illust: Illust) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        logger.info(f"[local] image {illust.id}")
        doc = await DownloadCache.find_one(DownloadCache.illust_id == illust.id, session=self.mongo.session())
        if doc is not None:
            _handle_expires_in(doc.metadata, self.conf.pixiv_download_cache_expires_in)
            yield doc.metadata
            yield doc.content
        else:
            raise NoSuchItemError()

    async def update_image(self, illust_id: int, content: bytes,
                           metadata: PixivRepoMetadata):
        logger.info(f"[local] update image {illust_id} "
                    f"{metadata}")

        await DownloadCache.find_one(
            DownloadCache.illust_id == illust_id,
            session=self.mongo.session()
        ).update(
            Set({
                DownloadCache.content: bson.Binary(content),
                DownloadCache.metadata: metadata
            }),
            upsert=True,
            session=self.mongo.session()
        )

    async def invalidate_all(self):
        logger.info(f"[local] invalidate_all")
        session = self.mongo.session()
        await DownloadCache.delete_all(session=session)
        await IllustDetailCache.delete_all(session=session)
        await UserDetailCache.delete_all(session=session)
        await IllustRankingCache.delete_all(session=session)
        await SearchIllustCache.delete_all(session=session)
        await SearchUserCache.delete_all(session=session)
        await UserIllustsCache.delete_all(session=session)
        await UserBookmarksCache.delete_all(session=session)
        await OtherIllustCache.delete_all(session=session)


__all__ = ("MongoPixivRepo",)

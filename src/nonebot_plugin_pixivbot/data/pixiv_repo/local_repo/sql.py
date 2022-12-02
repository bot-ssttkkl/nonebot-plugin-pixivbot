from datetime import datetime, timezone, timedelta
from functools import partial
from typing import AsyncGenerator, Union, Optional, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger
from sqlalchemy import select, delete

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.local_tag import LocalTagRepo
from nonebot_plugin_pixivbot.data.pixiv_repo import LazyIllust
from nonebot_plugin_pixivbot.data.pixiv_repo.errors import CacheExpiredError, NoSuchItemError
from nonebot_plugin_pixivbot.data.pixiv_repo.local_repo.sql_models import IllustDetailCache, UserDetailCache, \
    DownloadCache, IllustSetCache, IllustSetCacheIllust, UserSetCache, UserSetCacheUser
from nonebot_plugin_pixivbot.data.pixiv_repo.models import PixivRepoMetadata
from nonebot_plugin_pixivbot.data.source import with_session_scope
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.sql import insert
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from nonebot_plugin_pixivbot.utils.lifecycler import on_startup


def _handle_expires_in(metadata: PixivRepoMetadata, expires_in: int):
    if datetime.now(timezone.utc) - metadata.update_time >= timedelta(seconds=expires_in):
        raise CacheExpiredError(metadata)


def _extract_metadata(cache, is_set_cache):
    update_time = cache.update_time.replace(tzinfo=timezone.utc)

    if is_set_cache:
        metadata = PixivRepoMetadata(update_time=update_time, pages=cache.pages, next_qs=cache.next_qs)
    else:
        metadata = PixivRepoMetadata(update_time=update_time)
    return metadata


@context.inject
@context.register_singleton()
class SqlPixivRepo:
    conf: Config = Inject(Config)
    data_source: SqlDataSource = Inject(SqlDataSource)
    local_tag_repo: LocalTagRepo = Inject(LocalTagRepo)
    apscheduler: AsyncIOScheduler = Inject(AsyncIOScheduler)

    def __init__(self):
        on_startup(
            with_session_scope(partial(
                self.apscheduler.add_job,
                self.clean_expired,
                id='pixivbot_sql_pixiv_repo_clean_expired',
                trigger=IntervalTrigger(hours=2),
                max_instances=1
            )),
            replay=True
        )

    async def _get_illusts(self, cache_type: str,
                           key: dict,
                           expired_in: int,
                           offset: int = 0):
        session = self.data_source.session()
        stmt = (select(IllustSetCache)
                .where(IllustSetCache.cache_type == cache_type,
                       IllustSetCache.key == key))
        cache: Optional[IllustSetCache] = (await session.execute(stmt)).scalar_one_or_none()
        if cache is None:
            raise NoSuchItemError()

        metadata = _extract_metadata(cache, True)
        _handle_expires_in(metadata, expired_in)

        yield metadata.copy(update={"pages": 0})

        stmt = (select(IllustSetCacheIllust, IllustDetailCache)
                .where(IllustSetCacheIllust.cache_id == cache.id)
                .outerjoin(IllustDetailCache, IllustSetCacheIllust.illust_id == IllustDetailCache.illust_id)
                .order_by(IllustSetCacheIllust.rank)
                .offset(offset))

        total = 0
        broken = 0

        try:
            async for cache_illust, illust in await session.stream(stmt):
                cache_illust: IllustSetCacheIllust
                illust: Optional[IllustDetailCache]

                total += 1

                if illust is not None:
                    yield LazyIllust(illust.illust_id, Illust(**illust.illust))
                else:
                    yield LazyIllust(cache_illust.illust_id)
                    broken += 1
        finally:
            logger.info(f"[local] got {total} illusts, illust_detail of {broken} are missed")

        yield metadata

    async def _invalidate_illusts(self, cache_type: str, key: dict):
        session = self.data_source.session()
        stmt = (delete(IllustSetCache)
                .where(IllustSetCache.cache_type == cache_type,
                       IllustSetCache.key == key))
        await session.execute(stmt)
        await session.commit()

    async def _append_and_check_illusts(self, cache_type: str,
                                        key: dict,
                                        content: List[Union[Illust, LazyIllust]],
                                        metadata: PixivRepoMetadata,
                                        ranked: bool = False):
        session = self.data_source.session()

        async with session.begin_nested() as tx1:
            async with session.begin_nested() as tx2:
                stmt = (select(IllustSetCache)
                        .where(IllustSetCache.cache_type == cache_type,
                               IllustSetCache.key == key)
                        .limit(1))
                cache = (await session.execute(stmt)).scalar_one_or_none()
                if cache is None:
                    cache = IllustSetCache(cache_type=cache_type, key=key)
                    session.add(cache)

                cache.update_time = metadata.update_time
                cache.next_qs = metadata.next_qs
                cache.pages = metadata.pages

                # commit to get cache id
                await tx2.commit()

            if ranked:
                stmt = insert(IllustSetCacheIllust).values([
                    {"cache_id": cache.id, "illust_id": x.id, "rank": cache.size + i}
                    for i, x in enumerate(content)
                ]).on_conflict_do_nothing(index_elements=[
                    IllustSetCacheIllust.cache_id, IllustSetCacheIllust.illust_id
                ])
            else:
                stmt = insert(IllustSetCacheIllust).values([
                    {"cache_id": cache.id, "illust_id": x.id}
                    for i, x in enumerate(content)
                ]).on_conflict_do_nothing(index_elements=[
                    IllustSetCacheIllust.cache_id, IllustSetCacheIllust.illust_id
                ])

            row_count = (await session.execute(stmt)).rowcount
            if ranked:
                cache.size += row_count

            await tx1.commit()

        # insert illust detail
        values = []
        for x in content:
            if isinstance(x, LazyIllust):
                if not x.loaded:
                    continue
                x = x.content
            values.append(dict(illust_id=x.id, illust=x.dict(), update_time=metadata.update_time))
        if len(values) != 0:
            stmt = insert(IllustDetailCache).values(values)
            stmt = stmt.on_conflict_do_update(index_elements=[IllustDetailCache.illust_id],
                                              set_={
                                                  IllustDetailCache.illust: stmt.excluded.illust,
                                                  IllustDetailCache.update_time: stmt.excluded.update_time
                                              })
            await session.execute(stmt)
            await session.commit()

        # insert local tags
        li = []
        for x in content:
            if isinstance(x, LazyIllust):
                if not x.loaded:
                    continue
                x = x.content
            li.append(x)
        await self.local_tag_repo.update_from_illusts(li)

        return row_count != len(content)

    async def _get_users(self, cache_type: str,
                         key: dict,
                         expired_in: int,
                         offset: int = 0):
        session = self.data_source.session()
        stmt = (select(UserSetCache)
                .where(UserSetCache.cache_type == cache_type,
                       UserSetCache.key == key))
        cache = (await session.execute(stmt)).scalar_one_or_none()
        if cache is None:
            raise NoSuchItemError()

        metadata = _extract_metadata(cache, True)
        _handle_expires_in(metadata, expired_in)

        yield metadata.copy(update={"pages": 0})

        stmt = (select(UserSetCache, UserDetailCache)
                .where(UserSetCacheUser.cache_id == cache.id)
                .outerjoin(UserDetailCache, UserSetCacheUser.user_id == UserDetailCache.user_id)
                .offset(offset))

        total = 0
        try:
            async for cache_user, user in await session.stream(stmt):
                if user is not None:
                    yield User(**user.user)
                else:
                    yield User(id=cache_user.user_id, name="", account="")
                total += 1
        finally:
            logger.info(f"[local] got {total} users")

        yield metadata

    async def _invalidate_users(self, cache_type: str, key: dict):
        session = self.data_source.session()
        stmt = (delete(UserSetCache)
                .where(UserSetCache.cache_type == cache_type,
                       UserSetCache.key == key))
        await session.execute(stmt)
        await session.commit()

    async def _append_and_check_users(self, cache_type: str,
                                      key: dict,
                                      content: List[User],
                                      metadata: PixivRepoMetadata):
        session = self.data_source.session()

        async with session.begin_nested() as tx1:
            async with session.begin_nested() as tx2:
                stmt = (select(UserSetCache)
                        .where(UserSetCache.cache_type == cache_type,
                               UserSetCache.key == key)
                        .limit(1))
                cache = (await session.execute(stmt)).scalar_one_or_none()
                if cache is None:
                    cache = UserSetCache(cache_type=cache_type, key=key)
                    session.add(cache)

                cache.update_time = metadata.update_time
                cache.next_qs = metadata.next_qs
                cache.pages = metadata.pages

                # commit to get cache id
                await tx2.commit()

            stmt = insert(UserSetCacheUser).values([
                {"cache_id": cache.id, "user_id": x.id}
                for i, x in enumerate(content)
            ]).on_conflict_do_nothing(index_elements=[
                UserSetCacheUser.cache_id, UserSetCacheUser.user_id
            ])

            row_count = (await session.execute(stmt)).rowcount
            await tx1.commit()

        # insert user detail
        if len(content) != 0:
            values = [dict(user_id=x.id, user=x.dict(), update_time=metadata.update_time) for x in content]
            stmt = insert(UserDetailCache).values(values)
            await session.execute(stmt)
            await session.commit()

        return row_count != len(content)

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) \
            -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        logger.info(f"[local] illust_detail {illust_id}")

        session = self.data_source.session()
        stmt = select(IllustDetailCache).where(IllustDetailCache.illust_id == illust_id).limit(1)
        cache = (await session.execute(stmt)).scalar_one_or_none()

        if cache is not None:
            metadata = _extract_metadata(cache, False)
            _handle_expires_in(metadata, self.conf.pixiv_illust_detail_cache_expires_in)

            yield metadata
            yield Illust(**cache.illust)
        else:
            raise NoSuchItemError()

    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata):
        logger.info(f"[local] update illust_detail {illust.id} {metadata}")

        session = self.data_source.session()
        stmt = (insert(IllustDetailCache)
                .values(illust_id=illust.id, illust=illust.dict(), update_time=metadata.update_time))
        stmt = stmt.on_conflict_do_update(index_elements=[IllustDetailCache.illust_id],
                                          set_={
                                              IllustDetailCache.illust: stmt.excluded.illust,
                                              IllustDetailCache.update_time: stmt.excluded.update_time
                                          })

        await session.execute(stmt)
        await session.commit()

        if self.conf.pixiv_tag_translation_enabled:
            await self.local_tag_repo.update_from_illusts([illust])

    # ================ user_detail ================
    async def user_detail(self, user_id: int) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.info(f"[local] user_detail {user_id}")

        session = self.data_source.session()
        stmt = select(UserDetailCache).where(UserDetailCache.user_id == user_id).limit(1)
        cache = (await session.execute(stmt)).scalar_one_or_none()

        if cache is not None:
            metadata = _extract_metadata(cache, False)
            _handle_expires_in(metadata, self.conf.pixiv_user_detail_cache_expires_in)

            yield metadata
            yield User(**cache.user)
        else:
            raise NoSuchItemError()

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata):
        logger.info(f"[local] update user_detail {user.id} {metadata}")

        session = self.data_source.session()
        stmt = (insert(UserDetailCache)
                .values(user_id=user.id, user=user.dict(), update_time=metadata.update_time))
        stmt = stmt.on_conflict_do_update(index_elements=[UserDetailCache.user_id],
                                          set_={
                                              UserDetailCache.user: stmt.excluded.illust,
                                              UserDetailCache.update_time: stmt.excluded.update_time
                                          })

        await session.execute(stmt)
        await session.commit()

    # ================ image ================
    async def image(self, illust: Illust) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        logger.info(f"[local] image {illust.id}")

        session = self.data_source.session()
        stmt = select(DownloadCache).where(DownloadCache.illust_id == illust.id).limit(1)
        cache = (await session.execute(stmt)).scalar_one_or_none()

        if cache is not None:
            metadata = _extract_metadata(cache, False)
            _handle_expires_in(metadata, self.conf.pixiv_download_cache_expires_in)

            yield metadata
            yield cache.content
        else:
            raise NoSuchItemError()

    async def update_image(self, illust_id: int, content: bytes,
                           metadata: PixivRepoMetadata):
        logger.info(f"[local] update image {illust_id} {metadata}")

        session = self.data_source.session()
        stmt = (insert(DownloadCache)
                .values(illust_id=illust_id, content=content, update_time=metadata.update_time))
        stmt = stmt.on_conflict_do_update(index_elements=[DownloadCache.illust_id],
                                          set_={
                                              DownloadCache.content: stmt.excluded.content,
                                              DownloadCache.update_time: stmt.excluded.update_time
                                          })

        await session.execute(stmt)
        await session.commit()

    # ================ illust_ranking ================
    def illust_ranking(self, mode: Union[str, RankingMode], *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.info(f"[local] illust_ranking {mode}")

        return self._get_illusts("illust_ranking", {"mode": mode},
                                 expired_in=self.conf.pixiv_illust_ranking_cache_expires_in, offset=offset)

    async def invalidate_illust_ranking(self, mode: RankingMode):
        logger.info(f"[local] invalidate illust_ranking")
        await self._invalidate_illusts("illust_ranking", {"mode": mode})

    async def append_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append illust_ranking {mode} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("illust_ranking", {"mode": mode},
                                                    content=content, metadata=metadata,
                                                    ranked=True)

    # ================ search_illust ================
    def search_illust(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] search_illust {word}")
        return self._get_illusts("search_illust", {"word": word},
                                 expired_in=self.conf.pixiv_search_illust_cache_expires_in, offset=offset)

    async def invalidate_search_illust(self, word: str):
        logger.info(f"[local] invalidate search_illust {word}")
        await self._invalidate_illusts("search_illust", {"word": word})

    async def append_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        # 返回值表示content中是否有已经存在于集合的文档，下同
        logger.info(f"[local] append search_illust {word} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("search_illust", {"word": word},
                                                    content=content, metadata=metadata)

    # ================ user_illusts ================
    def user_illusts(self, user_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] user_illusts {user_id}")
        return self._get_illusts("user_illusts", {"user_id": user_id},
                                 expired_in=self.conf.pixiv_user_illusts_cache_expires_in, offset=offset)

    async def invalidate_user_illusts(self, user_id: int):
        logger.info(f"[local] invalidate user_illusts {user_id}")
        await self._invalidate_illusts("user_illusts", {"user_id": user_id})

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append user_illusts {user_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("user_illusts", {"user_id": user_id},
                                                    content=content, metadata=metadata)

    # ================ user_bookmarks ================
    def user_bookmarks(self, user_id: int = 0, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] user_bookmarks {user_id}")
        return self._get_illusts("user_bookmarks", {"user_id": user_id},
                                 expired_in=self.conf.pixiv_user_bookmarks_cache_expires_in, offset=offset)

    async def invalidate_user_bookmarks(self, user_id: int):
        logger.info(f"[local] invalidate user_bookmarks {user_id}")
        await self._invalidate_illusts("user_bookmarks", {"user_id": user_id})

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append user_bookmarks {user_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("user_bookmarks", {"user_id": user_id},
                                                    content=content, metadata=metadata)

    # ================ recommended_illusts ================
    def recommended_illusts(self, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] recommended_illusts")
        return self._get_illusts("other", {"type": "recommended_illusts"},
                                 expired_in=self.conf.pixiv_other_cache_expires_in, offset=offset)

    async def invalidate_recommended_illusts(self):
        logger.info(f"[local] invalidate recommended_illusts")
        await self._invalidate_illusts("other", {"type": "recommended_illusts"})

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append recommended_illusts "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("other", {"type": "recommended_illusts"},
                                                    content=content, metadata=metadata)

    # ================ related_illusts ================
    def related_illusts(self, illust_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.info(f"[local] related_illusts {illust_id}")
        return self._get_illusts("related_illusts", {"original_illust_id": illust_id},
                                 expired_in=self.conf.pixiv_related_illusts_cache_expires_in, offset=offset)

    async def invalidate_related_illusts(self, illust_id: int):
        logger.info(f"[local] invalidate related_illusts")
        await self._invalidate_illusts("related_illusts", {"original_illust_id": illust_id})

    async def append_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append related_illusts {illust_id} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_illusts("related_illusts", {"original_illust_id": illust_id},
                                                    content=content, metadata=metadata)

    # ================ search_user ================
    def search_user(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.info(f"[local] search_user {word}")
        return self._get_users("search_user", {"word": word},
                               expired_in=self.conf.pixiv_search_user_cache_expires_in, offset=offset)

    async def invalidate_search_user(self, word: str):
        logger.info(f"[local] invalidate search_user {word}")
        await self._invalidate_users("search_user", {"word": word})

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        logger.info(f"[local] append search_user {word} "
                    f"({len(content)} items) "
                    f"{metadata}")
        return await self._append_and_check_users("search_user", {"word": word},
                                                  content=content, metadata=metadata)

    async def invalidate_all(self):
        logger.info(f"[local] invalidate_all")

        session = self.data_source.session()
        result = await session.execute(delete(IllustSetCache))
        logger.success(f"[local] deleted {result.rowcount} illust_set cache")
        result = await session.execute(delete(UserSetCache))
        logger.success(f"[local] deleted {result.rowcount} user_set cache")
        result = await session.execute(delete(IllustDetailCache))
        logger.success(f"[local] deleted {result.rowcount} illust_detail cache")
        result = await session.execute(delete(UserDetailCache))
        logger.success(f"[local] deleted {result.rowcount} user_detail cache")
        result = await session.execute(delete(DownloadCache))
        logger.success(f"[local] deleted {result.rowcount} download cache")
        await session.commit()

    async def clean_expired(self):
        logger.info(f"[local] clean_expired")

        now = datetime.utcnow()
        session = self.data_source.session()
        stmt = delete(IllustDetailCache).where(
            IllustDetailCache.update_time <= now - timedelta(seconds=self.conf.pixiv_illust_detail_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} illust_detail cache")

        stmt = delete(UserDetailCache).where(
            UserDetailCache.update_time <= now - timedelta(seconds=self.conf.pixiv_user_detail_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} user_detail cache")

        stmt = delete(DownloadCache).where(
            DownloadCache.update_time <= now - timedelta(seconds=self.conf.pixiv_download_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} download cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'illust_ranking',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_illust_ranking_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} illust_ranking cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'search_illust',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_search_illust_cache_delete_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} search_illust cache")

        stmt = delete(UserSetCache).where(
            UserSetCache.cache_type == 'search_user',
            UserSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_search_user_cache_delete_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} search_user cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'user_illusts',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_user_illusts_cache_delete_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} user_illusts cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'user_bookmarks',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_user_bookmarks_cache_delete_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} user_bookmarks cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'related_illusts',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_related_illusts_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} related_illusts cache")

        stmt = delete(IllustSetCache).where(
            IllustSetCache.cache_type == 'other',
            IllustSetCache.update_time <= now - timedelta(seconds=self.conf.pixiv_other_cache_expires_in)
        )
        result = await session.execute(stmt)
        logger.success(f"[local] deleted {result.rowcount} other cache")

        await session.commit()

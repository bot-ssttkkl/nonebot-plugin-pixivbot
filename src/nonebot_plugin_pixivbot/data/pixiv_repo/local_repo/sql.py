from datetime import datetime, timezone, timedelta
from functools import partial
from typing import AsyncGenerator, Union, Optional, List

from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger
from nonebot_plugin_apscheduler import scheduler as apscheduler
from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import LocalPixivRepo
from .sql_models import IllustDetailCache, UserDetailCache, DownloadCache, IllustSetCache, IllustSetCacheIllust, \
    UserSetCache, UserSetCacheUser
from ..errors import CacheExpiredError, NoSuchItemError
from ..lazy_illust import LazyIllust
from ..models import PixivRepoMetadata
from ...local_tag import LocalTagRepo
from ...source.sql import DataSource
from ...utils.sql import insert
from ....config import Config
from ....enums import RankingMode
from ....global_context import context
from ....model import Illust, User
from ....utils.lifecycler import on_startup


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


conf = context.require(Config)
data_source = context.require(DataSource)
local_tags = context.require(LocalTagRepo)


@context.register_singleton()
class SqlPixivRepo(LocalPixivRepo):

    def __init__(self):
        on_startup(replay=True)(
            partial(
                apscheduler.add_job,
                self.clean_expired,
                id='pixivbot_sql_pixiv_repo_clean_expired',
                trigger=IntervalTrigger(hours=2),
                max_instances=1
            )
        )

    async def _get_illusts(self, session: AsyncSession,
                           cache_type: str,
                           key: dict,
                           expired_in: int,
                           offset: int = 0, ):
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
                .order_by(IllustSetCacheIllust.rank, IllustDetailCache.update_time.desc())
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
            logger.debug(f"[local] got {total} illusts, illust_detail of {broken} are missed")

        yield metadata

    async def _invalidate_illusts(self, session: AsyncSession,
                                  cache_type: str,
                                  key: dict):
        if conf.pixiv_sql_dialect == 'sqlite':
            await session.execute(text("PRAGMA foreign_keys = ON;"))

        stmt = (delete(IllustSetCache)
                .where(IllustSetCache.cache_type == cache_type,
                       IllustSetCache.key == key))
        await session.execute(stmt)
        await session.commit()

    async def _append_and_check_illusts(self, session: AsyncSession,
                                        cache_type: str,
                                        key: dict,
                                        content: List[Union[Illust, LazyIllust]],
                                        metadata: PixivRepoMetadata,
                                        append_at_begin: bool = False):
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

            row_count = 0
            if append_at_begin:
                stmt = select(
                    func.min(IllustSetCacheIllust.rank)
                ).select_from(IllustSetCacheIllust).where(
                    IllustSetCacheIllust.cache_id == cache.id
                )

                rnk = (await session.execute(stmt)).scalar_one_or_none()
                if rnk is None:
                    rnk = 0

                for x in reversed(content):
                    stmt = insert(IllustSetCacheIllust).values(
                        cache_id=cache.id, illust_id=x.id, rank=rnk - 1
                    ).on_conflict_do_nothing(index_elements=[
                        IllustSetCacheIllust.cache_id, IllustSetCacheIllust.illust_id
                    ])
                    result = await session.execute(stmt)
                    row_count += result.rowcount
                    rnk -= result.rowcount
            else:
                stmt = select(
                    func.max(IllustSetCacheIllust.rank)
                ).select_from(IllustSetCacheIllust).where(
                    IllustSetCacheIllust.cache_id == cache.id
                )

                rnk = (await session.execute(stmt)).scalar_one_or_none()
                if rnk is None:
                    rnk = 0

                for x in content:
                    stmt = insert(IllustSetCacheIllust).values(
                        cache_id=cache.id, illust_id=x.id, rank=rnk + 1
                    ).on_conflict_do_nothing(index_elements=[
                        IllustSetCacheIllust.cache_id, IllustSetCacheIllust.illust_id
                    ])
                    result = await session.execute(stmt)
                    row_count += result.rowcount
                    rnk += result.rowcount

            cache.size += row_count

            await tx1.commit()

        # insert illust detail
        for x in content:
            if isinstance(x, LazyIllust):
                if not x.loaded:
                    continue
                x = x.content

            stmt = insert(IllustDetailCache).values(
                illust_id=x.id, illust=x.dict(), update_time=metadata.update_time
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[IllustDetailCache.illust_id],
                set_={
                    IllustDetailCache.illust: stmt.excluded.illust,
                    IllustDetailCache.update_time: stmt.excluded.update_time
                }
            )
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
        await local_tags.update_from_illusts(li)

        return row_count != len(content)

    async def _get_users(self, session: AsyncSession,
                         cache_type: str,
                         key: dict,
                         expired_in: int,
                         offset: int = 0):
        stmt = (select(UserSetCache)
                .where(UserSetCache.cache_type == cache_type,
                       UserSetCache.key == key))
        cache = (await session.execute(stmt)).scalar_one_or_none()
        if cache is None:
            raise NoSuchItemError()

        metadata = _extract_metadata(cache, True)
        _handle_expires_in(metadata, expired_in)

        yield metadata.copy(update={"pages": 0})

        stmt = (select(UserSetCacheUser, UserDetailCache)
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
            logger.debug(f"[local] got {total} users")

        yield metadata

    async def _invalidate_users(self, session: AsyncSession,
                                cache_type: str,
                                key: dict):
        if conf.pixiv_sql_dialect == 'sqlite':
            await session.execute(text("PRAGMA foreign_keys = ON;"))

        stmt = (delete(UserSetCache)
                .where(UserSetCache.cache_type == cache_type,
                       UserSetCache.key == key))
        await session.execute(stmt)
        await session.commit()

    async def _append_and_check_users(self, session: AsyncSession,
                                      cache_type: str,
                                      key: dict,
                                      content: List[User],
                                      metadata: PixivRepoMetadata):

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

            row_count = 0
            for x in content:
                stmt = insert(UserSetCacheUser).values(
                    cache_id=cache.id, user_id=x.id
                ).on_conflict_do_nothing(index_elements=[
                    UserSetCacheUser.cache_id, UserSetCacheUser.user_id
                ])
                row_count += (await session.execute(stmt)).rowcount

            await tx1.commit()

        # insert user detail
        for x in content:
            stmt = insert(UserDetailCache).values(
                user_id=x.id, user=x.dict(), update_time=metadata.update_time
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[UserDetailCache.user_id],
                set_={
                    UserDetailCache.user: stmt.excluded.user,
                    UserDetailCache.update_time: stmt.excluded.update_time
                }
            )
            await session.execute(stmt)
            await session.commit()

        return row_count != len(content)

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) \
            -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        logger.debug(f"[local] illust_detail {illust_id}")

        async with data_source.start_session() as session:
            stmt = select(IllustDetailCache).where(IllustDetailCache.illust_id == illust_id).limit(1)
            cache = (await session.execute(stmt)).scalar_one_or_none()

            if cache is not None:
                metadata = _extract_metadata(cache, False)
                _handle_expires_in(metadata, conf.pixiv_illust_detail_cache_expires_in)

                yield metadata
                yield Illust(**cache.illust)
            else:
                raise NoSuchItemError()

    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update illust_detail {illust.id} {metadata}")

        async with data_source.start_session() as session:
            stmt = (insert(IllustDetailCache)
                    .values(illust_id=illust.id, illust=illust.dict(), update_time=metadata.update_time))
            stmt = stmt.on_conflict_do_update(index_elements=[IllustDetailCache.illust_id],
                                              set_={
                                                  IllustDetailCache.illust: stmt.excluded.illust,
                                                  IllustDetailCache.update_time: stmt.excluded.update_time
                                              })

            await session.execute(stmt)
            await session.commit()

            if conf.pixiv_tag_translation_enabled:
                await local_tags.update_from_illusts([illust])

    # ================ user_detail ================
    async def user_detail(self, user_id: int) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_detail {user_id}")

        async with data_source.start_session() as session:
            stmt = select(UserDetailCache).where(UserDetailCache.user_id == user_id).limit(1)
            cache = (await session.execute(stmt)).scalar_one_or_none()

            if cache is not None:
                metadata = _extract_metadata(cache, False)
                _handle_expires_in(metadata, conf.pixiv_user_detail_cache_expires_in)

                yield metadata
                yield User(**cache.user)
            else:
                raise NoSuchItemError()

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update user_detail {user.id} {metadata}")

        async with data_source.start_session() as session:
            stmt = (insert(UserDetailCache)
                    .values(user_id=user.id, user=user.dict(), update_time=metadata.update_time))
            stmt = stmt.on_conflict_do_update(index_elements=[UserDetailCache.user_id],
                                              set_={
                                                  UserDetailCache.user: stmt.excluded.user,
                                                  UserDetailCache.update_time: stmt.excluded.update_time
                                              })

            await session.execute(stmt)
            await session.commit()

    # ================ image ================
    async def image(self, illust: Illust, page: int = 0) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        logger.debug(f"[local] image {illust.id}")

        async with data_source.start_session() as session:
            stmt = select(DownloadCache).where(DownloadCache.illust_id == illust.id,
                                               DownloadCache.page == page).limit(1)
            cache = (await session.execute(stmt)).scalar_one_or_none()

            if cache is not None:
                metadata = _extract_metadata(cache, False)
                _handle_expires_in(metadata, conf.pixiv_download_cache_expires_in)

                yield metadata
                yield cache.content
            else:
                raise NoSuchItemError()

    async def update_image(self, illust_id: int, page: int,
                           content: bytes, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update image {illust_id} {metadata}")

        async with data_source.start_session() as session:
            stmt = (insert(DownloadCache)
                    .values(illust_id=illust_id, page=page, content=content, update_time=metadata.update_time))
            stmt = stmt.on_conflict_do_update(index_elements=[DownloadCache.illust_id, DownloadCache.page],
                                              set_={
                                                  DownloadCache.content: stmt.excluded.content,
                                                  DownloadCache.update_time: stmt.excluded.update_time
                                              })

            await session.execute(stmt)
            await session.commit()

    # ================ illust_ranking ================
    async def illust_ranking(self, mode: Union[str, RankingMode], *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.debug(f"[local] illust_ranking {mode}")

        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "illust_ranking", {"mode": mode},
                                             expired_in=conf.pixiv_illust_ranking_cache_expires_in, offset=offset):
                yield x

    async def invalidate_illust_ranking(self, mode: RankingMode):
        logger.debug(f"[local] invalidate illust_ranking")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "illust_ranking", {"mode": mode})

    async def append_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append illust_ranking {mode} "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "illust_ranking", {"mode": mode},
                                                        content=content, metadata=metadata)

    # ================ search_illust ================
    async def search_illust(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_illust {word}")
        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "search_illust", {"word": word},
                                             expired_in=conf.pixiv_search_illust_cache_expires_in, offset=offset):
                yield x

    async def invalidate_search_illust(self, word: str):
        logger.debug(f"[local] invalidate search_illust {word}")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "search_illust", {"word": word})

    async def append_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        # 返回值表示content中是否有已经存在于集合的文档，下同
        logger.debug(f"[local] append search_illust {word} "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "search_illust", {"word": word},
                                                        content=content, metadata=metadata)

    # ================ user_illusts ================
    async def user_illusts(self, user_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_illusts {user_id}")
        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "user_illusts", {"user_id": user_id},
                                             expired_in=conf.pixiv_user_illusts_cache_expires_in, offset=offset):
                yield x

    async def invalidate_user_illusts(self, user_id: int):
        logger.debug(f"[local] invalidate user_illusts {user_id}")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "user_illusts", {"user_id": user_id})

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata,
                                  append_at_begin: bool = False) -> bool:
        logger.debug(f"[local] append user_illusts {user_id} "
                     f"{'at begin ' if append_at_begin else ''}"
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "user_illusts", {"user_id": user_id},
                                                        content=content, metadata=metadata,
                                                        append_at_begin=append_at_begin)

    # ================ user_bookmarks ================
    async def user_bookmarks(self, user_id: int = 0, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_bookmarks {user_id}")
        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "user_bookmarks", {"user_id": user_id},
                                             expired_in=conf.pixiv_user_bookmarks_cache_expires_in, offset=offset):
                yield x

    async def invalidate_user_bookmarks(self, user_id: int):
        logger.debug(f"[local] invalidate user_bookmarks {user_id}")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "user_bookmarks", {"user_id": user_id})

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata,
                                    append_at_begin: bool = False) -> bool:
        logger.debug(f"[local] append user_bookmarks {user_id} "
                     f"{'at begin ' if append_at_begin else ''} "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "user_bookmarks", {"user_id": user_id},
                                                        content=content, metadata=metadata,
                                                        append_at_begin=append_at_begin)

    # ================ recommended_illusts ================
    async def recommended_illusts(self, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] recommended_illusts")
        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "other", {"type": "recommended_illusts"},
                                             expired_in=conf.pixiv_other_cache_expires_in, offset=offset):
                yield x

    async def invalidate_recommended_illusts(self):
        logger.debug(f"[local] invalidate recommended_illusts")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "other", {"type": "recommended_illusts"})

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append recommended_illusts "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "other", {"type": "recommended_illusts"},
                                                        content=content, metadata=metadata)

    # ================ related_illusts ================
    async def related_illusts(self, illust_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] related_illusts {illust_id}")
        async with data_source.start_session() as session:
            async for x in self._get_illusts(session, "related_illusts", {"original_illust_id": illust_id},
                                             expired_in=conf.pixiv_related_illusts_cache_expires_in,
                                             offset=offset):
                yield x

    async def invalidate_related_illusts(self, illust_id: int):
        logger.debug(f"[local] invalidate related_illusts")
        async with data_source.start_session() as session:
            await self._invalidate_illusts(session, "related_illusts", {"original_illust_id": illust_id})

    async def append_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append related_illusts {illust_id} "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_illusts(session, "related_illusts", {"original_illust_id": illust_id},
                                                        content=content, metadata=metadata)

    # ================ search_user ================
    async def search_user(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_user {word}")
        async with data_source.start_session() as session:
            async for x in self._get_users(session, "search_user", {"word": word},
                                           expired_in=conf.pixiv_search_user_cache_expires_in, offset=offset):
                yield x

    async def invalidate_search_user(self, word: str):
        logger.debug(f"[local] invalidate search_user {word}")
        async with data_source.start_session() as session:
            await self._invalidate_users(session, "search_user", {"word": word})

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append search_user {word} "
                     f"({len(content)} items) "
                     f"{metadata}")
        async with data_source.start_session() as session:
            return await self._append_and_check_users(session, "search_user", {"word": word},
                                                      content=content, metadata=metadata)

    async def invalidate_all(self):
        logger.debug(f"[local] invalidate_all")

        async with data_source.start_session() as session:
            if conf.pixiv_sql_dialect == 'sqlite':
                await session.execute(text("PRAGMA foreign_keys = ON;"))

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
        logger.debug(f"[local] clean_expired")

        async with data_source.start_session() as session:
            if conf.pixiv_sql_dialect == 'sqlite':
                await session.execute(text("PRAGMA foreign_keys = ON;"))

            now = datetime.utcnow()
            stmt = delete(IllustDetailCache).where(
                IllustDetailCache.update_time <= now - timedelta(seconds=conf.pixiv_illust_detail_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} illust_detail cache")

            stmt = delete(UserDetailCache).where(
                UserDetailCache.update_time <= now - timedelta(seconds=conf.pixiv_user_detail_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} user_detail cache")

            stmt = delete(DownloadCache).where(
                DownloadCache.update_time <= now - timedelta(seconds=conf.pixiv_download_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} download cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'illust_ranking',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_illust_ranking_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} illust_ranking cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'search_illust',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_search_illust_cache_delete_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} search_illust cache")

            stmt = delete(UserSetCache).where(
                UserSetCache.cache_type == 'search_user',
                UserSetCache.update_time <= now - timedelta(seconds=conf.pixiv_search_user_cache_delete_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} search_user cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'user_illusts',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_user_illusts_cache_delete_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} user_illusts cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'user_bookmarks',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_user_bookmarks_cache_delete_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} user_bookmarks cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'related_illusts',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_related_illusts_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} related_illusts cache")

            stmt = delete(IllustSetCache).where(
                IllustSetCache.cache_type == 'other',
                IllustSetCache.update_time <= now - timedelta(seconds=conf.pixiv_other_cache_expires_in)
            )
            result = await session.execute(stmt)
            logger.success(f"[local] deleted {result.rowcount} other cache")

            await session.commit()

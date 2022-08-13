from datetime import datetime, timedelta
from functools import partial
from typing import Any, AsyncGenerator, List, NamedTuple

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.utils.shared_agen import SharedAsyncGeneratorManager
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from . import LazyIllust
from .abstract_repo import AbstractPixivRepo
from .abstract_repo import PixivRepoMetadata
from .enums import *
from .local_repo import LocalPixivRepo
from .mediator import mediate_single, mediate_many, mediate_append
from .pkg_context import context
from .remote_repo import RemotePixivRepo


class SharedAgenIdentifier(NamedTuple):
    type: int
    arg: Any


@context.inject
@context.register_singleton()
class PixivSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[SharedAgenIdentifier, Any]):
    log_tag = "pixiv_shared_agen"

    conf: Config
    local: LocalPixivRepo
    remote: RemotePixivRepo

    def calc_expires_time(self, identifier: SharedAgenIdentifier, update_time: datetime) -> datetime:
        if identifier.type == ILLUST_DETAIL:
            return update_time + timedelta(seconds=self.conf.pixiv_illust_detail_cache_expires_in)
        elif identifier.type == USER_DETAIL:
            return update_time + timedelta(seconds=self.conf.pixiv_user_detail_cache_expires_in)
        elif identifier.type == SEARCH_ILLUST:
            return update_time + timedelta(seconds=self.conf.pixiv_search_illust_cache_expires_in)
        elif identifier.type == SEARCH_USER:
            return update_time + timedelta(seconds=self.conf.pixiv_search_user_cache_expires_in)
        elif identifier.type == USER_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_user_illusts_cache_expires_in)
        elif identifier.type == USER_BOOKMARKS:
            return update_time + timedelta(seconds=self.conf.pixiv_user_bookmarks_cache_expires_in)
        elif identifier.type == RECOMMENDED_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_other_cache_expires_in)
        elif identifier.type == RELATED_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_related_illusts_cache_expires_in)
        elif identifier.type == ILLUST_RANKING:
            return update_time + timedelta(seconds=self.conf.pixiv_illust_ranking_cache_expires_in)
        elif identifier.type == IMAGE:
            return update_time + timedelta(seconds=self.conf.pixiv_download_cache_expires_in)
        else:
            raise ValueError("invalid identifier: " + str(identifier))

    async def on_agen_next(self, identifier: SharedAgenIdentifier, item: Any):
        if isinstance(item, PixivRepoMetadata) and not self.get_expires_time(identifier):
            expires_time = self.calc_expires_time(identifier, item.update_time)
            self.set_expires_time(identifier, expires_time)

    def illust_detail_factory(self, illust_id: int,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[Illust, None]:
        return mediate_single(
            cache_factory=partial(self.local.illust_detail, illust_id=illust_id),
            remote_factory=partial(self.remote.illust_detail, illust_id=illust_id),
            cache_updater=lambda data, metadata: self.local.update_illust_detail(data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_detail_factory(self, user_id: int,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return mediate_single(
            cache_factory=partial(self.local.user_detail, user_id=user_id),
            remote_factory=partial(self.remote.user_detail, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_detail(data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_illust_factory(self, word: str,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=partial(self.local.search_illust, word=word),
            remote_factory=partial(self.remote.search_illust, word=word),
            cache_updater=lambda data, metadata: self.local.update_search_illust(word, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_search_illust(word, data, metadata),
            max_item=self.conf.pixiv_random_illust_max_item,
            max_page=self.conf.pixiv_random_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_user_factory(self, word: str,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return mediate_many(
            cache_factory=partial(self.local.search_user, word=word),
            remote_factory=partial(self.remote.search_user, word=word),
            cache_updater=lambda data, metadata: self.local.update_search_user(word, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_search_user(word, data, metadata),
            max_page=1,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_illusts_factory(self, user_id: int,
                             cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=partial(self.local.user_illusts, user_id=user_id),
            remote_factory=partial(self.remote.user_illusts, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_illusts(user_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_user_illusts(user_id, data, metadata),
            max_item=self.conf.pixiv_random_user_illust_max_item,
            max_page=self.conf.pixiv_random_user_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_bookmarks_factory(self, user_id: int,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=partial(self.local.user_bookmarks, user_id=user_id),
            remote_factory=partial(self.remote.user_bookmarks, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_bookmarks(user_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_user_bookmarks(user_id, data, metadata),
            max_item=self.conf.pixiv_random_bookmark_max_item,
            max_page=self.conf.pixiv_random_bookmark_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def recommended_illusts_factory(self, cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=self.local.recommended_illusts,
            remote_factory=self.remote.recommended_illusts,
            cache_updater=lambda data, metadata: self.local.update_recommended_illusts(data, metadata),
            cache_appender=lambda data, metadata: self.local.append_recommended_illusts(data, metadata),
            max_item=self.conf.pixiv_random_recommended_illust_max_item,
            max_page=self.conf.pixiv_random_recommended_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def related_illusts_factory(self, illust_id: int,
                                cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=partial(self.local.related_illusts, illust_id),
            remote_factory=partial(self.remote.related_illusts, illust_id),
            cache_updater=lambda data, metadata: self.local.update_related_illusts(illust_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_related_illusts(illust_id, data, metadata),
            max_item=self.conf.pixiv_random_related_illust_max_item,
            max_page=self.conf.pixiv_random_related_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def illust_ranking_factory(self, mode: RankingMode,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[List[LazyIllust], None]:
        return mediate_many(
            cache_factory=partial(self.local.illust_ranking, mode),
            remote_factory=partial(self.remote.illust_ranking, mode),
            cache_updater=lambda data, metadata: self.local.update_illust_ranking(mode, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_illust_ranking(mode, data, metadata),
            max_item=self.conf.pixiv_ranking_fetch_item,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def image_factory(self, illust: Illust,
                      cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_single(
            cache_factory=partial(self.local.image, illust),
            remote_factory=partial(self.remote.image, illust),
            cache_updater=lambda data, metadata: self.local.update_image(illust.id, data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def agen_factory(self, identifier: SharedAgenIdentifier,
                     cache_strategy: CacheStrategy = CacheStrategy.NORMAL,
                     *args, **kwargs) -> AsyncGenerator[Any, None]:
        if identifier.type == ILLUST_DETAIL:
            return self.illust_detail_factory(identifier.arg, cache_strategy)
        elif identifier.type == USER_DETAIL:
            return self.user_detail_factory(identifier.arg, cache_strategy)
        elif identifier.type == SEARCH_ILLUST:
            return self.search_illust_factory(identifier.arg, cache_strategy)
        elif identifier.type == SEARCH_USER:
            return self.search_user_factory(identifier.arg, cache_strategy)
        elif identifier.type == USER_ILLUSTS:
            return self.user_illusts_factory(identifier.arg, cache_strategy)
        elif identifier.type == USER_BOOKMARKS:
            return self.user_bookmarks_factory(identifier.arg, cache_strategy)
        elif identifier.type == RECOMMENDED_ILLUSTS:
            return self.recommended_illusts_factory(cache_strategy)
        elif identifier.type == RELATED_ILLUSTS:
            return self.related_illusts_factory(identifier.arg, cache_strategy)
        elif identifier.type == ILLUST_RANKING:
            return self.illust_ranking_factory(identifier.arg, cache_strategy)
        elif identifier.type == IMAGE:
            return self.image_factory(kwargs.get("illust", None) or args[0], cache_strategy)
        else:
            raise ValueError("invalid identifier: " + str(identifier))


@context.inject
@context.root.register_singleton()
class PixivRepo(AbstractPixivRepo):
    _shared_agen_mgr: PixivSharedAsyncGeneratorManager
    _local: LocalPixivRepo
    _remote: RemotePixivRepo

    async def invalidate_cache(self):
        await self._local.invalidate_cache()

    async def illust_detail(self, illust_id: int,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[Illust, None]:
        logger.info(f"[repo] illust_detail {illust_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(ILLUST_DETAIL, illust_id), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_detail(self, user_id: int,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] user_detail {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(USER_DETAIL, user_id), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_illust(self, word: str,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] search_illust {word} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(SEARCH_ILLUST, word), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_user(self, word: str,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] search_user {word} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(SEARCH_USER, word), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_illusts(self, user_id: int = 0,
                           cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_illusts {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(USER_ILLUSTS, user_id), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_bookmarks(self, user_id: int = 0,
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_bookmarks {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(USER_BOOKMARKS, user_id), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def recommended_illusts(self, cache_strategy: CacheStrategy = CacheStrategy.NORMAL) \
            -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] recommended_illusts "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(RECOMMENDED_ILLUSTS, None), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def related_illusts(self, illust_id: int,
                              cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] related_illusts {illust_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(RELATED_ILLUSTS, illust_id), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def illust_ranking(self, mode: RankingMode,
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] illust_ranking {mode} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(ILLUST_RANKING, mode), cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def image(self, illust: Illust,
                    cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[bytes, None]:
        logger.info(f"[repo] image {illust.id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(IMAGE, illust.id), cache_strategy, illust) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x


__all__ = ('PixivRepo',)

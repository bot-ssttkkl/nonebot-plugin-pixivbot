from datetime import datetime, timedelta
from functools import partial
from typing import Any, AsyncGenerator, List, Tuple

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
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
from .shared_agen import SharedAsyncGeneratorManager


@context.inject
@context.register_singleton()
class PixivSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[Tuple[int, Any], Any]):
    conf: Config
    local: LocalPixivRepo
    remote: RemotePixivRepo

    def calc_expires_time(self, identifier: Tuple[int, Any], update_time: datetime) -> datetime:
        if identifier[0] == ILLUST_DETAIL:
            return update_time + timedelta(seconds=self.conf.pixiv_illust_detail_cache_expires_in)
        elif identifier[0] == USER_DETAIL:
            return update_time + timedelta(seconds=self.conf.pixiv_user_detail_cache_expires_in)
        elif identifier[0] == SEARCH_ILLUST:
            return update_time + timedelta(seconds=self.conf.pixiv_search_illust_cache_expires_in)
        elif identifier[0] == SEARCH_USER:
            return update_time + timedelta(seconds=self.conf.pixiv_search_user_cache_expires_in)
        elif identifier[0] == USER_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_user_illusts_cache_expires_in)
        elif identifier[0] == USER_BOOKMARKS:
            return update_time + timedelta(seconds=self.conf.pixiv_user_bookmarks_cache_expires_in)
        elif identifier[0] == RECOMMENDED_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_other_cache_expires_in)
        elif identifier[0] == RELATED_ILLUSTS:
            return update_time + timedelta(seconds=self.conf.pixiv_related_illusts_cache_expires_in)
        elif identifier[0] == ILLUST_RANKING:
            return update_time + timedelta(seconds=self.conf.pixiv_illust_ranking_cache_expires_in)
        elif identifier[0] == IMAGE:
            return update_time + timedelta(seconds=self.conf.pixiv_download_cache_expires_in)
        else:
            raise ValueError("invalid identifier: " + str(identifier))

    async def on_agen_next(self, identifier: Tuple[int, Any], item: Any):
        if isinstance(item, PixivRepoMetadata) and not self.get_expires_time(identifier):
            self.set_expires_time(identifier, self.calc_expires_time(identifier, item.update_time))

    def illust_detail_factory(self, illust_id: int) -> AsyncGenerator[Illust, None]:
        return mediate_single(
            cache_factory=partial(self.local.illust_detail, illust_id=illust_id),
            remote_factory=partial(self.remote.illust_detail, illust_id=illust_id),
            cache_updater=lambda data, metadata: self.local.update_illust_detail(data, metadata)
        )

    def user_detail_factory(self, user_id: int) -> AsyncGenerator[User, None]:
        return mediate_single(
            cache_factory=partial(self.local.user_detail, user_id=user_id),
            remote_factory=partial(self.remote.user_detail, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_detail(data, metadata)
        )

    def search_illust_factory(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=partial(self.local.search_illust, word=word),
            remote_factory=partial(self.remote.search_illust, word=word),
            cache_updater=lambda data, metadata: self.local.update_search_illust(word, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_search_illust(word, data, metadata),
            max_item=self.conf.pixiv_random_illust_max_item,
            max_page=self.conf.pixiv_random_illust_max_page,
        )

    def search_user_factory(self, word: str) -> AsyncGenerator[User, None]:
        return mediate_many(
            cache_factory=partial(self.local.search_user, word=word),
            remote_factory=partial(self.remote.search_user, word=word),
            cache_updater=lambda data, metadata: self.local.update_search_user(word, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_search_user(word, data, metadata),
            max_page=1,
        )

    def user_illusts_factory(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=partial(self.local.user_illusts, user_id=user_id),
            remote_factory=partial(self.remote.user_illusts, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_illusts(user_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_user_illusts(user_id, data, metadata),
            max_item=self.conf.pixiv_random_user_illust_max_item,
            max_page=self.conf.pixiv_random_user_illust_max_page,
        )

    def user_bookmarks_factory(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=partial(self.local.user_bookmarks, user_id=user_id),
            remote_factory=partial(self.remote.user_bookmarks, user_id=user_id),
            cache_updater=lambda data, metadata: self.local.update_user_bookmarks(user_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_user_bookmarks(user_id, data, metadata),
            max_item=self.conf.pixiv_random_bookmark_max_item,
            max_page=self.conf.pixiv_random_bookmark_max_page,
        )

    def recommended_illusts_factory(self) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=self.local.recommended_illusts,
            remote_factory=self.remote.recommended_illusts,
            cache_updater=lambda data, metadata: self.local.update_recommended_illusts(data, metadata),
            cache_appender=lambda data, metadata: self.local.append_recommended_illusts(data, metadata),
            max_item=self.conf.pixiv_random_recommended_illust_max_item,
            max_page=self.conf.pixiv_random_recommended_illust_max_page,
        )

    def related_illusts_factory(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=partial(self.local.related_illusts, illust_id),
            remote_factory=partial(self.remote.related_illusts, illust_id),
            cache_updater=lambda data, metadata: self.local.update_related_illusts(illust_id, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_related_illusts(illust_id, data, metadata),
            max_item=self.conf.pixiv_random_related_illust_max_item,
            max_page=self.conf.pixiv_random_related_illust_max_page,
        )

    def illust_ranking_factory(self, mode: RankingMode) -> AsyncGenerator[List[LazyIllust], None]:
        return mediate_many(
            cache_factory=partial(self.local.illust_ranking, mode),
            remote_factory=partial(self.remote.illust_ranking, mode),
            cache_updater=lambda data, metadata: self.local.update_illust_ranking(mode, data, metadata),
            cache_appender=lambda data, metadata: self.local.append_illust_ranking(mode, data, metadata),
            max_item=self.conf.pixiv_ranking_fetch_item,
        )

    def image_factory(self, illust: Illust) -> AsyncGenerator[LazyIllust, None]:
        return mediate_single(
            cache_factory=partial(self.local.image, illust),
            remote_factory=partial(self.remote.image, illust),
            cache_updater=lambda data, metadata: self.local.update_image(illust.id, data, metadata)
        )

    def agen_factory(self, identifier: Tuple[int, Any], *args, **kwargs) -> AsyncGenerator[Any, None]:
        if identifier[0] == ILLUST_DETAIL:
            return self.illust_detail_factory(identifier[1])
        elif identifier[0] == USER_DETAIL:
            return self.user_detail_factory(identifier[1])
        elif identifier[0] == SEARCH_ILLUST:
            return self.search_illust_factory(identifier[1])
        elif identifier[0] == SEARCH_USER:
            return self.search_user_factory(identifier[1])
        elif identifier[0] == USER_ILLUSTS:
            return self.user_illusts_factory(identifier[1])
        elif identifier[0] == USER_BOOKMARKS:
            return self.user_bookmarks_factory(identifier[1])
        elif identifier[0] == RECOMMENDED_ILLUSTS:
            return self.recommended_illusts_factory()
        elif identifier[0] == RELATED_ILLUSTS:
            return self.related_illusts_factory(identifier[1])
        elif identifier[0] == ILLUST_RANKING:
            return self.illust_ranking_factory(identifier[1])
        elif identifier[0] == IMAGE:
            return self.image_factory(kwargs.get("illust", None) or args[0])
        else:
            raise ValueError("invalid identifier: " + str(identifier))


@context.inject
@context.root.register_singleton()
class PixivRepo(AbstractPixivRepo):
    _shared_agen_mgr: PixivSharedAsyncGeneratorManager
    _local: LocalPixivRepo

    async def invalidate_cache(self):
        await self._local.invalidate_cache()

    async def illust_detail(self, illust_id: int) -> AsyncGenerator[Illust, None]:
        logger.info(f"[repo] illust_detail {illust_id}")
        with self._shared_agen_mgr.get((ILLUST_DETAIL, illust_id)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_detail(self, user_id: int) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] user_detail {user_id}")
        with self._shared_agen_mgr.get((USER_DETAIL, user_id)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] search_illust {word}")
        with self._shared_agen_mgr.get((SEARCH_ILLUST, word)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] search_user {word}")
        with self._shared_agen_mgr.get((SEARCH_USER, word)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_illusts(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_illusts {user_id}")
        with self._shared_agen_mgr.get((USER_ILLUSTS, user_id)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_bookmarks {user_id}")
        with self._shared_agen_mgr.get((USER_BOOKMARKS, user_id)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] recommended_illusts")
        with self._shared_agen_mgr.get((RECOMMENDED_ILLUSTS, None)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] related_illusts {illust_id}")
        with self._shared_agen_mgr.get((RELATED_ILLUSTS, illust_id)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def illust_ranking(self, mode: RankingMode) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] illust_ranking {mode}")
        with self._shared_agen_mgr.get((ILLUST_RANKING, mode)) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def image(self, illust: Illust) -> AsyncGenerator[bytes, None]:
        logger.info(f"[repo] image {illust.id}")
        with self._shared_agen_mgr.get((IMAGE, illust.id), illust) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x


__all__ = ('PixivRepo',)

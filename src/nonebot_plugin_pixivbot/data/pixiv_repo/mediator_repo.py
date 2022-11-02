from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Union

from frozendict import frozendict
from nonebot import logger
from pydantic import BaseModel

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User, UserPreview
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from .enums import PixivResType, CacheStrategy
from .lazy_illust import LazyIllust
from .local_repo import LocalPixivRepo
from .mediator import mediate_single, mediate_many, mediate_append
from .models import PixivRepoMetadata
from .remote_repo import RemotePixivRepo


class SharedAgenIdentifier(BaseModel):
    type: PixivResType
    kwargs: frozendict[str, Any]

    def __init__(self, type: PixivResType, **kwargs):
        super().__init__(type=type, kwargs=frozendict(kwargs))

    def __str__(self):
        return f"({self.type.name} {', '.join(map(lambda k: f'{k}={self.kwargs[k]}', {**self.kwargs}))})"

    class Config:
        frozen = True


@context.inject
@context.register_singleton()
class PixivSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[SharedAgenIdentifier, Any]):
    log_tag = "pixiv_shared_agen"

    conf = Inject(Config)
    local = Inject(LocalPixivRepo)
    remote = Inject(RemotePixivRepo)

    def illust_detail_factory(self, illust_id: int,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[Illust, None]:
        return mediate_single(
            cache_factory=self.local.illust_detail,
            remote_factory=self.remote.illust_detail,
            query_kwargs={"illust_id": illust_id},
            cache_updater=lambda data, metadata: self.local.update_illust_detail(data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_detail_factory(self, user_id: int,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return mediate_single(
            cache_factory=self.local.user_detail,
            remote_factory=self.remote.user_detail,
            query_kwargs={"user_id": user_id},
            cache_updater=lambda data, metadata: self.local.update_user_detail(data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_illust_factory(self, word: str,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=self.local.search_illust,
            remote_factory=self.remote.search_illust,
            query_kwargs={"word": word},
            cache_appender=lambda data, metadata: self.local.append_search_illust(word, data, metadata),
            max_item=self.conf.pixiv_random_illust_max_item,
            max_page=self.conf.pixiv_random_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_user_factory(self, word: str,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return mediate_append(
            cache_factory=self.local.search_user,
            remote_factory=self.remote.search_user,
            query_kwargs={"word": word},
            cache_appender=lambda data, metadata: self.local.append_search_user(word, data, metadata),
            max_page=1,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_illusts_factory(self, user_id: int,
                             cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=self.local.user_illusts,
            remote_factory=self.remote.user_illusts,
            query_kwargs={"user_id": user_id},
            cache_appender=lambda data, metadata: self.local.append_user_illusts(user_id, data, metadata),
            max_item=self.conf.pixiv_random_user_illust_max_item,
            max_page=self.conf.pixiv_random_user_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_bookmarks_factory(self, user_id: int,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_append(
            cache_factory=self.local.user_bookmarks,
            remote_factory=self.remote.user_bookmarks,
            query_kwargs={"user_id": user_id},
            cache_appender=lambda data, metadata: self.local.append_user_bookmarks(user_id, data, metadata),
            max_item=self.conf.pixiv_random_bookmark_max_item,
            max_page=self.conf.pixiv_random_bookmark_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def recommended_illusts_factory(self, cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=self.local.recommended_illusts,
            remote_factory=self.remote.recommended_illusts,
            query_kwargs={},
            cache_invalidator=self.local.invalidate_recommended_illusts,
            cache_appender=lambda data, metadata: self.local.append_recommended_illusts(data, metadata),
            max_item=self.conf.pixiv_random_recommended_illust_max_item,
            max_page=self.conf.pixiv_random_recommended_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def related_illusts_factory(self, illust_id: int,
                                cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=self.local.related_illusts,
            remote_factory=self.remote.related_illusts,
            query_kwargs={"illust_id": illust_id},
            cache_invalidator=lambda: self.local.invalidate_related_illusts(illust_id),
            cache_appender=lambda data, metadata: self.local.append_related_illusts(illust_id, data, metadata),
            max_item=self.conf.pixiv_random_related_illust_max_item,
            max_page=self.conf.pixiv_random_related_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def illust_ranking_factory(self, mode: RankingMode,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return mediate_many(
            cache_factory=self.local.illust_ranking,
            remote_factory=self.remote.illust_ranking,
            query_kwargs={"mode": mode},
            cache_invalidator=lambda: self.local.invalidate_illust_ranking(mode),
            cache_appender=lambda data, metadata: self.local.append_illust_ranking(mode, data, metadata),
            max_item=self.conf.pixiv_ranking_fetch_item,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def image_factory(self, illust_id: int, illust: Illust,
                      cache_strategy: CacheStrategy) -> AsyncGenerator[bytes, None]:
        return mediate_single(
            cache_factory=self.local.image,
            remote_factory=self.remote.image,
            query_kwargs={"illust": illust},
            cache_updater=lambda data, metadata: self.local.update_image(illust.id, data, metadata),
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    factories = {
        PixivResType.ILLUST_DETAIL: illust_detail_factory,
        PixivResType.USER_DETAIL: user_detail_factory,
        PixivResType.SEARCH_ILLUST: search_illust_factory,
        PixivResType.SEARCH_USER: search_user_factory,
        PixivResType.USER_ILLUSTS: user_illusts_factory,
        PixivResType.USER_BOOKMARKS: user_bookmarks_factory,
        PixivResType.RECOMMENDED_ILLUSTS: recommended_illusts_factory,
        PixivResType.RELATED_ILLUSTS: related_illusts_factory,
        PixivResType.ILLUST_RANKING: illust_ranking_factory,
        PixivResType.IMAGE: image_factory,
    }

    def agen(self, identifier: SharedAgenIdentifier, cache_strategy: CacheStrategy, **kwargs) -> AsyncGenerator[
        Any, None]:
        if identifier.type in self.factories:
            merged_kwargs = identifier.kwargs | kwargs
            # noinspection PyTypeChecker
            return self.factories[identifier.type](self, cache_strategy=cache_strategy, **merged_kwargs)
        else:
            raise ValueError("invalid identifier: " + str(identifier))

    expires_in = {
        PixivResType.ILLUST_DETAIL: timedelta(seconds=context.require(Config).pixiv_illust_detail_cache_expires_in),
        PixivResType.USER_DETAIL: timedelta(seconds=context.require(Config).pixiv_user_detail_cache_expires_in),
        PixivResType.SEARCH_ILLUST: timedelta(seconds=context.require(Config).pixiv_search_illust_cache_expires_in),
        PixivResType.SEARCH_USER: timedelta(seconds=context.require(Config).pixiv_search_user_cache_expires_in),
        PixivResType.USER_ILLUSTS: timedelta(seconds=context.require(Config).pixiv_user_illusts_cache_expires_in),
        PixivResType.USER_BOOKMARKS: timedelta(seconds=context.require(Config).pixiv_user_bookmarks_cache_expires_in),
        PixivResType.RECOMMENDED_ILLUSTS: timedelta(seconds=context.require(Config).pixiv_other_cache_expires_in),
        PixivResType.RELATED_ILLUSTS: timedelta(seconds=context.require(Config).pixiv_related_illusts_cache_expires_in),
        PixivResType.ILLUST_RANKING: timedelta(seconds=context.require(Config).pixiv_illust_ranking_cache_expires_in),
        PixivResType.IMAGE: timedelta(seconds=context.require(Config).pixiv_download_cache_expires_in),
    }

    def calc_expires_time(self, identifier: SharedAgenIdentifier, update_time: datetime) -> datetime:
        if identifier.type in self.factories:
            return update_time + self.expires_in[identifier.type]
        else:
            raise ValueError("invalid identifier: " + str(identifier))

    async def on_agen_next(self, identifier: SharedAgenIdentifier, item: Any):
        if isinstance(item, PixivRepoMetadata) and not self.get_expires_time(identifier):
            expires_time = self.calc_expires_time(identifier, item.update_time)
            self.set_expires_time(identifier, expires_time)


@context.inject
@context.root.register_singleton()
class MediatorPixivRepo:
    _shared_agen_mgr = Inject(PixivSharedAsyncGeneratorManager)
    _local = Inject(LocalPixivRepo)
    _remote = Inject(RemotePixivRepo)

    async def invalidate_cache(self):
        self._shared_agen_mgr.invalidate_all()
        await self._local.invalidate_all()

    async def illust_detail(self, illust_id: int,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[Illust, None]:
        logger.info(f"[mediator] illust_detail {illust_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.ILLUST_DETAIL, illust_id=illust_id),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_detail(self, user_id: int,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.info(f"[mediator] user_detail {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_DETAIL, user_id=user_id),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_illust(self, word: str,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] search_illust {word} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.SEARCH_ILLUST, word=word),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_user(self, word: str,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.info(f"[mediator] search_user {word} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.SEARCH_USER, word=word),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_bookmarks(self, user_id: int = 0,
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] user_bookmarks {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_BOOKMARKS, user_id=user_id),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_illusts(self, user_id: int = 0,
                           cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] user_illusts {user_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_ILLUSTS, user_id=user_id),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def _contact_user_illusts_with_preview(self, user_preview: UserPreview,
                                                 cache_strategy: CacheStrategy = CacheStrategy.NORMAL) \
            -> AsyncGenerator[LazyIllust, None]:
        for illust in user_preview.illusts:
            yield LazyIllust(illust.id, illust)

        ids = {x.id for x in user_preview.illusts}

        if len(user_preview.illusts) >= 3:
            gen = self.user_illusts(user_preview.user.id, cache_strategy)

            async for x in gen:
                if x.id not in ids:
                    yield x

    async def user_following_illusts(self, user_id: int,
                                     cache_strategy: CacheStrategy = CacheStrategy.NORMAL) \
            -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] user_following_illusts {user_id} "
                    f"cache_strategy={cache_strategy.name}")

        n = 0
        gen = []
        peeked = []

        async for user_preview in self._remote.user_following_with_preview(user_id):
            if not isinstance(user_preview, PixivRepoMetadata):
                n += 1
                gen.append(self._contact_user_illusts_with_preview(user_preview, cache_strategy))
                peeked.append(None)

        try:
            while True:
                select = -1
                for i in range(n):
                    try:
                        if not peeked[i]:
                            peeked[i] = await gen[i].__anext__()

                        if select == -1 or peeked[i].create_date > peeked[select].create_date:
                            select = i
                    except StopAsyncIteration:
                        pass

                if select == -1:
                    break

                yield peeked[select]
                peeked[select] = None
        except GeneratorExit:
            for gen in gen:
                await gen.aclose()

    async def recommended_illusts(self, cache_strategy: CacheStrategy = CacheStrategy.NORMAL) \
            -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] recommended_illusts "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.RECOMMENDED_ILLUSTS),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def related_illusts(self, illust_id: int,
                              cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[mediator] related_illusts {illust_id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.RELATED_ILLUSTS, illust_id=illust_id),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def illust_ranking(self, mode: Union[str, RankingMode],
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.info(f"[mediator] illust_ranking {mode} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.ILLUST_RANKING, mode=mode),
                                       cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def image(self, illust: Illust,
                    cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[bytes, None]:
        logger.info(f"[mediator] image {illust.id} "
                    f"cache_strategy={cache_strategy.name}")
        with self._shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.IMAGE, illust_id=illust.id),
                                       cache_strategy, illust=illust) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x


__all__ = ('MediatorPixivRepo',)

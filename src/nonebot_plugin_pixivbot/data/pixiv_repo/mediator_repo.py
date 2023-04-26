from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Union

from frozendict import frozendict
from nonebot import logger
from pydantic import BaseModel

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Illust, User, UserPreview
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from .base import PixivRepo
from .enums import PixivResType, CacheStrategy
from .lazy_illust import LazyIllust
from .local_repo import LocalPixivRepo
from .mediator import SingleMediator, AppendMediator, ManyMediator
from .models import PixivRepoMetadata
from .remote_repo import RemotePixivRepo
from ...utils.format import format_kwargs

conf = context.require(Config)
local = context.require(LocalPixivRepo)
remote = context.require(RemotePixivRepo)


class SharedAgenIdentifier(BaseModel):
    type: PixivResType
    kwargs: frozendict[str, Any]

    def __init__(self, type: PixivResType, **kwargs):
        super().__init__(type=type, kwargs=frozendict(kwargs))

    def __str__(self):
        return f"({self.type.name} {format_kwargs(**self.kwargs)})"

    class Config:
        frozen = True


class PixivSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[SharedAgenIdentifier, Any]):
    log_tag = "pixiv_shared_agen"

    mediators = {
        "illust_detail": SingleMediator(
            "illust_detail",
            cache_factory=lambda kwargs: local.illust_detail(kwargs["illust_id"]),
            remote_factory=lambda kwargs: remote.illust_detail(**kwargs),
            cache_updater=lambda kwargs, data, meta: local.update_illust_detail(data, meta)
        ),
        "user_detail": SingleMediator(
            "user_detail",
            cache_factory=lambda kwargs: local.user_detail(kwargs["user_id"]),
            remote_factory=lambda kwargs: remote.user_detail(**kwargs),
            cache_updater=lambda kwargs, data, meta: local.update_user_detail(data, meta)
        ),
        "search_illust": AppendMediator(
            "search_illust",
            cache_factory=lambda kwargs: local.search_illust(kwargs["word"]),
            remote_factory=lambda kwargs: remote.search_illust(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_search_illust(kwargs["word"]),
            cache_appender=lambda kwargs, data, meta: local.append_search_illust(kwargs["word"], data, meta),
            front_cache_appender=lambda kwargs, data, meta: local.append_search_illust(kwargs["word"], data, meta),
        ),
        "search_user": AppendMediator(
            "search_user",
            cache_factory=lambda kwargs: local.search_user(kwargs["word"]),
            remote_factory=lambda kwargs: remote.search_user(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_search_user(kwargs["word"]),
            cache_appender=lambda kwargs, data, meta: local.append_search_user(kwargs["word"], data, meta),
            front_cache_appender=lambda kwargs, data, meta: local.append_search_user(kwargs["word"], data, meta),
        ),
        "user_illusts": AppendMediator(
            "user_illusts",
            cache_factory=lambda kwargs: local.user_illusts(kwargs["user_id"]),
            remote_factory=lambda kwargs: remote.user_illusts(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_user_illusts(kwargs["user_id"]),
            cache_appender=lambda kwargs, data, meta: local.append_user_illusts(kwargs["user_id"], data, meta),
            front_cache_appender=lambda kwargs, data, meta: local.append_user_illusts(kwargs["user_id"], data, meta,
                                                                                      append_at_begin=True),
        ),
        "user_bookmarks": AppendMediator(
            "user_bookmarks",
            cache_factory=lambda kwargs: local.user_bookmarks(kwargs["user_id"]),
            remote_factory=lambda kwargs: remote.user_bookmarks(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_user_bookmarks(kwargs["user_id"]),
            cache_appender=lambda kwargs, data, meta: local.append_user_bookmarks(kwargs["user_id"], data, meta),
            front_cache_appender=lambda kwargs, data, meta: local.append_user_bookmarks(kwargs["user_id"], data, meta,
                                                                                        append_at_begin=True),
        ),
        "recommended_illusts": ManyMediator(
            "recommended_illusts",
            cache_factory=lambda kwargs: local.recommended_illusts(),
            remote_factory=lambda kwargs: remote.recommended_illusts(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_recommended_illusts(),
            cache_appender=lambda kwargs, data, meta: local.append_recommended_illusts(data, meta),
        ),
        "related_illusts": ManyMediator(
            "related_illusts",
            cache_factory=lambda kwargs: local.related_illusts(kwargs["illust_id"]),
            remote_factory=lambda kwargs: remote.related_illusts(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_related_illusts(kwargs["illust_id"]),
            cache_appender=lambda kwargs, data, meta: local.append_related_illusts(kwargs["illust_id"], data, meta),
        ),
        "illust_ranking": ManyMediator(
            "illust_ranking",
            cache_factory=lambda kwargs: local.illust_ranking(kwargs["mode"]),
            remote_factory=lambda kwargs: remote.illust_ranking(**kwargs),
            cache_invalidator=lambda kwargs: local.invalidate_illust_ranking(kwargs["mode"]),
            cache_appender=lambda kwargs, data, meta: local.append_illust_ranking(kwargs["mode"], data, meta),
        ),
        "image": SingleMediator(
            "image",
            cache_factory=lambda kwargs: local.image(kwargs["illust"], kwargs["page"]),
            remote_factory=lambda kwargs: remote.image(**kwargs),
            cache_updater=lambda kwargs, data, meta: local.update_image(kwargs["illust"].id, kwargs["page"], data, meta)
        ),
    }

    def illust_detail_factory(self, illust_id: int,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[Illust, None]:
        return self.mediators["illust_detail"].mediate(
            {"illust_id": illust_id},
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_detail_factory(self, user_id: int,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return self.mediators["user_detail"].mediate(
            query_kwargs={"user_id": user_id},
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_illust_factory(self, word: str,
                              cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["search_illust"].mediate(
            query_kwargs={"word": word},
            max_item=conf.pixiv_random_illust_max_item,
            max_page=conf.pixiv_random_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def search_user_factory(self, word: str,
                            cache_strategy: CacheStrategy) -> AsyncGenerator[User, None]:
        return self.mediators["search_user"].mediate(
            query_kwargs={"word": word},
            max_page=1,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_illusts_factory(self, user_id: int,
                             cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["user_illusts"].mediate(
            query_kwargs={"user_id": user_id},
            max_item=conf.pixiv_random_user_illust_max_item,
            max_page=conf.pixiv_random_user_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def user_bookmarks_factory(self, user_id: int,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["user_bookmarks"].mediate(
            query_kwargs={"user_id": user_id},
            max_item=conf.pixiv_random_bookmark_max_item,
            max_page=conf.pixiv_random_bookmark_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def recommended_illusts_factory(self, cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["recommended_illusts"].mediate(
            query_kwargs={},
            max_item=conf.pixiv_random_recommended_illust_max_item,
            max_page=conf.pixiv_random_recommended_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def related_illusts_factory(self, illust_id: int,
                                cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["related_illusts"].mediate(
            query_kwargs={"illust_id": illust_id},
            max_item=conf.pixiv_random_related_illust_max_item,
            max_page=conf.pixiv_random_related_illust_max_page,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def illust_ranking_factory(self, mode: RankingMode,
                               cache_strategy: CacheStrategy) -> AsyncGenerator[LazyIllust, None]:
        return self.mediators["illust_ranking"].mediate(
            query_kwargs={"mode": mode},
            max_item=conf.pixiv_ranking_fetch_item,
            force_expiration=cache_strategy == CacheStrategy.FORCE_EXPIRATION,
        )

    def image_factory(self, illust_id: int, illust: Illust, page: int,
                      cache_strategy: CacheStrategy) -> AsyncGenerator[bytes, None]:
        return self.mediators["image"].mediate(
            query_kwargs={"illust": illust, "page": page},
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

    def agen(self, identifier: SharedAgenIdentifier,
             cache_strategy: CacheStrategy, **kwargs) -> AsyncGenerator[Any, None]:
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
        await super().on_agen_next(identifier, item)
        if isinstance(item, PixivRepoMetadata) and not self.get_expires_time(identifier):
            expires_time = self.calc_expires_time(identifier, item.update_time)
            await self.set_expires_time(identifier, expires_time.timestamp())


@context.root.register_singleton()
class MediatorPixivRepo(PixivRepo):
    def __init__(self):
        self.shared_agen_mgr = PixivSharedAsyncGeneratorManager()

    async def invalidate_cache(self):
        await self.shared_agen_mgr.invalidate_all()
        await local.invalidate_all()

    async def illust_detail(self, illust_id: int,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[Illust, None]:
        logger.debug(f"[mediator] illust_detail {illust_id} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.ILLUST_DETAIL, illust_id=illust_id),
                                            cache_strategy) as gen:
            data = None
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    data = x

        # 保证shared_agen能正常结束
        if data is not None:
            yield data

    async def user_detail(self, user_id: int,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.debug(f"[mediator] user_detail {user_id} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_DETAIL, user_id=user_id),
                                            cache_strategy) as gen:
            data = None
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    data = x

        # 保证shared_agen能正常结束
        if data is not None:
            yield data

    async def search_illust(self, word: str,
                            cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[mediator] search_illust {word} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.SEARCH_ILLUST, word=word),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def search_user(self, word: str,
                          cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[User, None]:
        logger.debug(f"[mediator] search_user {word} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.SEARCH_USER, word=word),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_bookmarks(self, user_id: int = 0,
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[mediator] user_bookmarks {user_id} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_BOOKMARKS, user_id=user_id),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def user_illusts(self, user_id: int = 0,
                           cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[mediator] user_illusts {user_id} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.USER_ILLUSTS, user_id=user_id),
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
        logger.debug(f"[mediator] user_following_illusts {user_id} "
                     f"cache_strategy={cache_strategy.name}")

        n = 0
        gen = []
        peeked = []

        async for user_preview in remote.user_following_with_preview(user_id):
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
        logger.debug(f"[mediator] recommended_illusts "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.RECOMMENDED_ILLUSTS),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def related_illusts(self, illust_id: int,
                              cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[mediator] related_illusts {illust_id} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.RELATED_ILLUSTS, illust_id=illust_id),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def illust_ranking(self, mode: Union[str, RankingMode],
                             cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[LazyIllust, None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.debug(f"[mediator] illust_ranking {mode} "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.ILLUST_RANKING, mode=mode),
                                            cache_strategy) as gen:
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    yield x

    async def image(self, illust: Illust, page: int = 0,
                    cache_strategy: CacheStrategy = CacheStrategy.NORMAL) -> AsyncGenerator[bytes, None]:
        logger.debug(f"[mediator] image {illust.id}[{page}] "
                     f"cache_strategy={cache_strategy.name}")
        async with self.shared_agen_mgr.get(SharedAgenIdentifier(PixivResType.IMAGE, illust_id=illust.id, page=page),
                                            cache_strategy, illust=illust) as gen:
            data = None
            async for x in gen:
                if not isinstance(x, PixivRepoMetadata):
                    data = x

        # 保证shared_agen能正常退出
        if data is not None:
            yield data


__all__ = ('MediatorPixivRepo',)

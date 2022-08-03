from functools import partial
from inspect import isawaitable
from typing import List, Tuple, AsyncGenerator, Optional, TypeVar, Callable, Union, Awaitable

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_mediator import AbstractMediator
from .abstract_repo import AbstractPixivRepo
from .lazy_illust import LazyIllust
from .local_repo import LocalPixivRepo, CacheExpiredError, NoSuchItemError
from .pkg_context import context
from .remote_repo import RemotePixivRepo

T = TypeVar("T")

SEARCH_ILLUST = 0
SEARCH_USER = 1
USER_ILLUSTS = 2
USER_BOOKMARKS = 3
RECOMMENDED_ILLUSTS = 4
ILLUST_RANKING = 5
ILLUST_DETAIL = 6
IMAGE = 7
RELATED_ILLUSTS = 8
USER_DETAIL = 9


async def mixin(cache_loader: Callable[[], Union[T, Awaitable[T]]],
                remote_fetcher: Callable[[], Union[T, Awaitable[T]]],
                hook_on_cache: Optional[Callable[[T], T]] = None,
                hook_on_fetch: Optional[Callable[[T], T]] = None) \
        -> AsyncGenerator[T, None]:
    try:
        cache = cache_loader()
        if isawaitable(cache):
            cache = await cache

        if hook_on_cache:
            cache = hook_on_cache(cache)
        yield cache
    except (CacheExpiredError, NoSuchItemError):
        result = remote_fetcher()
        if isawaitable(result):
            result = await result

        if hook_on_fetch:
            result = hook_on_fetch(result)
        yield result


async def mixin_agen(cache_loader: Callable[[], AsyncGenerator[T, None]],
                     remote_fetcher: Callable[[], AsyncGenerator[T, None]]) \
        -> AsyncGenerator[T, None]:
    try:
        async for x in cache_loader():
            yield x
    except (CacheExpiredError, NoSuchItemError):
        async for x in remote_fetcher():
            yield x


async def mixin_append_agen(cache_loader: Callable[[], AsyncGenerator[T, None]],
                            remote_fetcher: Callable[[], AsyncGenerator[T, None]],
                            cache_appender: Callable[[List[T]], Awaitable[bool]]) \
        -> AsyncGenerator[T, None]:
    try:
        async for x in cache_loader():
            yield x
    except NoSuchItemError:
        async for x in remote_fetcher():
            yield x
    except CacheExpiredError:
        # if cache expired, pick new bookmarks from remote
        buffer = []
        async for illust in remote_fetcher():
            buffer.append(illust)
            if len(buffer) >= 20:
                if await cache_appender(buffer):
                    break
                buffer = []
        else:
            if len(buffer) > 0:
                await cache_appender(buffer)

        async for x in cache_loader():
            yield x


T_ID = TypeVar("T_ID")


@context.inject
@context.register_singleton()
class PixivMediator(AbstractMediator[T_ID]):
    conf: Config
    local: LocalPixivRepo
    remote: RemotePixivRepo

    def illust_detail_factory(self, illust_id: int) -> AsyncGenerator[Illust, None]:
        return mixin(
            cache_loader=partial(self.local.illust_detail, illust_id=illust_id),
            remote_fetcher=partial(self.remote.illust_detail, illust_id=illust_id)
        )

    def user_detail_factory(self, user_id: int) -> AsyncGenerator[User, None]:
        return mixin(
            cache_loader=partial(self.local.user_detail, user_id=user_id),
            remote_fetcher=partial(self.remote.user_detail, user_id=user_id)
        )

    def search_illust_factory(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        return mixin_agen(
            cache_loader=partial(self.local.search_illust, word=word),
            remote_fetcher=partial(self.remote.search_illust, word=word),
        )

    def search_user_factory(self, word: str) -> AsyncGenerator[User, None]:
        return mixin_agen(
            cache_loader=partial(self.local.search_user, word=word),
            remote_fetcher=partial(self.remote.search_user, word=word),
        )

    def user_illusts_factory(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mixin_append_agen(
            cache_loader=partial(self.local.user_illusts, user_id=user_id),
            remote_fetcher=partial(self.remote.user_illusts, user_id=user_id),
            cache_appender=partial(self.local.append_user_illusts, user_id=user_id),
        )

    def user_bookmarks_factory(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mixin_append_agen(
            cache_loader=partial(self.local.user_bookmarks, user_id=user_id),
            remote_fetcher=partial(self.remote.user_bookmarks, user_id=user_id),
            cache_appender=partial(self.local.append_user_bookmarks, user_id=user_id),
        )

    def recommended_illusts_factory(self) -> AsyncGenerator[LazyIllust, None]:
        return mixin_agen(
            cache_loader=self.local.recommended_illusts,
            remote_fetcher=self.remote.recommended_illusts
        )

    def related_illusts_factory(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        return mixin_agen(
            cache_loader=partial(self.local.related_illusts, illust_id=illust_id),
            remote_fetcher=partial(self.remote.related_illusts, illust_id=illust_id),
        )

    def illust_ranking_factory(self, mode: RankingMode) -> AsyncGenerator[List[LazyIllust], None]:
        range = 1, self.conf.pixiv_ranking_fetch_item
        return mixin(
            cache_loader=partial(self.local.illust_ranking, mode=mode, range=range),
            remote_fetcher=partial(self.remote.illust_ranking, mode=mode, range=range)
        )

    def image_factory(self, illust: Illust) -> AsyncGenerator[LazyIllust, None]:
        return mixin(
            cache_loader=partial(self.local.image, illust=illust),
            remote_fetcher=partial(self.remote.image, illust=illust),
        )

    def agen_factory(self, identifier: T_ID, *args, **kwargs) -> AsyncGenerator[T, None]:
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

    async def on_agen_stop(self, identifier: T_ID, items: List[T]):
        if identifier[0] == ILLUST_DETAIL:
            return await self.local.update_illust_detail(items[0])
        elif identifier[0] == USER_DETAIL:
            return await self.local.update_user_detail(items[0])
        elif identifier[0] == SEARCH_ILLUST:
            return await self.local.update_search_illust(identifier[1], items)
        elif identifier[0] == SEARCH_USER:
            return await self.local.update_search_user(identifier[1], items)
        elif identifier[0] == USER_ILLUSTS:
            pass
            # return await self.local.update_user_illusts(identifier[1], items)
        elif identifier[0] == USER_BOOKMARKS:
            pass
            # return await self.local.update_user_bookmarks(identifier[1], items)
        elif identifier[0] == RECOMMENDED_ILLUSTS:
            return await self.local.update_recommended_illusts(items)
        elif identifier[0] == RELATED_ILLUSTS:
            return await self.local.update_related_illusts(identifier[1], items)
        elif identifier[0] == ILLUST_RANKING:
            return await self.local.update_illust_ranking(identifier[1], items[0])
        elif identifier[0] == IMAGE:
            return await self.local.update_image(identifier[1], items[0])
        else:
            raise ValueError("invalid identifier: " + str(identifier))


@context.inject
@context.root.register_singleton()
class PixivRepo(AbstractPixivRepo):
    _mediator: PixivMediator
    _local: LocalPixivRepo

    async def invalidate_cache(self):
        await self._local.invalidate_cache()

    async def illust_detail(self, illust_id: int) -> Illust:
        logger.info(f"[repo] illust_detail {illust_id}")
        with self._mediator.get((ILLUST_DETAIL, illust_id)) as gen:
            async for x in gen:
                return x

    async def user_detail(self, user_id: int) -> User:
        logger.info(f"[repo] user_detail {user_id}")
        with self._mediator.get((USER_DETAIL, user_id)) as gen:
            async for x in gen:
                return x

    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] search_illust {word}")
        with self._mediator.get((SEARCH_ILLUST, word)) as gen:
            async for x in gen:
                yield x

    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] search_user {word}")
        with self._mediator.get((SEARCH_USER, word)) as gen:
            async for x in gen:
                yield x

    async def user_illusts(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_illusts {user_id}")
        with self._mediator.get((USER_ILLUSTS, user_id)) as gen:
            async for x in gen:
                yield x

    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_bookmarks {user_id}")
        with self._mediator.get((USER_BOOKMARKS, user_id)) as gen:
            async for x in gen:
                yield x

    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] recommended_illusts")
        with self._mediator.get((RECOMMENDED_ILLUSTS,)) as gen:
            async for x in gen:
                yield x

    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] related_illusts {illust_id}")
        with self._mediator.get((RELATED_ILLUSTS, illust_id)) as gen:
            async for x in gen:
                yield x

    async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[LazyIllust]:
        logger.info(f"[repo] illust_ranking {mode} {range[0]}~{range[1]}")
        with self._mediator.get((ILLUST_RANKING, mode)) as gen:
            async for items in gen:
                return items[range[0] - 1:range[1]]

    async def image(self, illust: Illust) -> bytes:
        logger.info(f"[repo] image {illust.id}")
        with self._mediator.get((IMAGE, illust.id), illust) as gen:
            async for x in gen:
                return x


__all__ = ('PixivRepo',)

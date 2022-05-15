import typing
from functools import partial

from nonebot import get_driver

from .abstract_data_source import AbstractDataSource
from .remote_data_source import RemoteDataSource
from .cache_data_source import CacheDataSource
from .cache_manager import CacheManager
from .pkg_context import context
from ...config import Config
from ...model import Illust, User, LazyIllust


@context.export_singleton()
class PixivDataSource(AbstractDataSource):
    remote: RemoteDataSource = context.require(RemoteDataSource)
    cache: CacheDataSource = context.require(CacheDataSource)

    _conf: Config = context.require(Config)
    timeout = _conf.pixiv_query_timeout

    def __init__(self):
        self._cache_manager = CacheManager()

    def start(self):
        self.remote.start()

    async def shutdown(self):
        await self.shutdown()

    async def invalidate_cache(self):
        self.cache.invalidate_cache()

    async def illust_detail(self, illust_id: int) -> Illust:
        return await self._cache_manager.get(
            identifier=(6, illust_id),
            cache_loader=partial(self.cache.illust_detail,
                                 illust_id=illust_id),
            remote_fetcher=partial(
                self.remote.illust_detail, illust_id=illust_id),
            cache_updater=lambda content: self.cache.update_illust_detail(
                illust_id, content),
            timeout=self.timeout
        )

    async def search_illust(self, word: str) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(0, word),
            cache_loader=partial(self.cache.search_illust, word=word),
            remote_fetcher=partial(self.remote.search_illust, word=word),
            cache_updater=lambda content: self.cache.update_search_illust(
                word, content),
            timeout=self.timeout
        )

    async def search_user(self, word: str) -> typing.List[User]:
        return await self._cache_manager.get(
            identifier=(1, word),
            cache_loader=partial(self.cache.search_user, word=word),
            remote_fetcher=partial(self.remote.search_user, word=word),
            cache_updater=lambda content: self.cache.update_search_user(
                word, content),
            timeout=self.timeout
        )

    async def user_illusts(self, user_id: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(2, user_id),
            cache_loader=partial(self.cache.user_illusts, user_id=user_id),
            remote_fetcher=partial(self.remote.user_illusts, user_id=user_id),
            cache_updater=lambda content: self.cache.update_user_illusts(
                user_id, content),
            timeout=self.timeout
        )

    async def user_bookmarks(self, user_id: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(3, user_id),
            cache_loader=partial(self.cache.user_bookmarks, user_id=user_id),
            remote_fetcher=partial(
                self.remote.user_bookmarks, user_id=user_id),
            cache_updater=lambda content: self.cache.update_user_bookmarks(
                user_id, content),
            timeout=self.timeout
        )

    async def recommended_illusts(self) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(4,),
            cache_loader=self.cache.recommended_illusts,
            remote_fetcher=self.remote.recommended_illusts,
            cache_updater=self.cache.update_recommended_illusts,
            timeout=self.timeout
        )

    async def related_illusts(self, illust_id: int) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(8, illust_id),
            cache_loader=partial(
                self.cache.related_illusts, illust_id=illust_id),
            remote_fetcher=partial(
                self.remote.related_illusts, illust_id=illust_id),
            cache_updater=lambda content: self.cache.update_related_illusts(
                illust_id, content),
            timeout=self.timeout
        )

    async def illust_ranking(self, mode: str = 'day') -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(5, mode),
            cache_loader=partial(
                self.cache.illust_ranking, mode=mode),
            remote_fetcher=partial(
                self.remote.illust_ranking, mode=mode),
            cache_updater=lambda content: self.cache.update_illust_ranking(
                mode, content),
            timeout=self.timeout
        )

    async def image(self, illust: Illust) -> bytes:
        return await self._cache_manager.get(
            identifier=(7, illust.id),
            cache_loader=partial(self.cache.image, illust=illust),
            remote_fetcher=partial(self.remote.image, illust=illust),
            cache_updater=lambda content: self.cache.update_image(
                illust, content),
            timeout=self.timeout
        )


pixiv_data_source = context.require(PixivDataSource)

get_driver().on_startup(pixiv_data_source.start)
get_driver().on_shutdown(pixiv_data_source.shutdown)


__all__ = ('PixivDataSource', )

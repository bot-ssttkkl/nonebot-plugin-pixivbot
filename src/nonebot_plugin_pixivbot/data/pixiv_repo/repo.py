import typing
from functools import partial

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo
from .lazy_illust import LazyIllust
from .local_repo import LocalPixivRepo
from .mediator import Mediator
from .pkg_context import context
from .remote_repo import RemotePixivRepo
from ...utils.lifecycler import on_startup, on_shutdown


def do_skip_and_limit(items: list, skip: int, limit: int) -> list:
    if skip:
        if limit and len(items) > skip + limit:
            return items[skip:skip + limit]
        else:
            return items[skip:]
    elif limit and len(items) > limit:
        return items[:limit]
    else:
        return items


@context.root.register_singleton()
class PixivRepo(AbstractPixivRepo):
    _conf: Config = context.require(Config)

    def __init__(self):
        self._mediator = None
        self.remote = context.require(RemotePixivRepo)
        self.cache = context.require(LocalPixivRepo)

        on_startup(self.start, replay=True)
        on_shutdown(self.shutdown)

    async def start(self):
        await self.remote.start()
        self._mediator = Mediator()

    async def shutdown(self):
        await self.remote.shutdown()

    def invalidate_cache(self):
        return self.cache.invalidate_cache()

    async def illust_detail(self, illust_id: int) -> Illust:
        return await self._mediator.get(
            identifier=(6, illust_id),
            cache_loader=partial(self.cache.illust_detail,
                                 illust_id=illust_id),
            remote_fetcher=partial(
                self.remote.illust_detail, illust_id=illust_id),
            cache_updater=self.cache.update_illust_detail,
            timeout=self._conf.pixiv_query_timeout
        )

    async def user_detail(self, user_id: int) -> User:
        return await self._mediator.get(
            identifier=(9, user_id),
            cache_loader=partial(self.cache.user_detail,
                                 user_id=user_id),
            remote_fetcher=partial(
                self.remote.user_detail, user_id=user_id),
            cache_updater=self.cache.update_user_detail,
            timeout=self._conf.pixiv_query_timeout
        )

    async def search_illust(self, word: str, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        # skip和limit只作用于cache_loader
        return await self._mediator.get(
            identifier=(0, word),
            cache_loader=partial(self.cache.search_illust,
                                 word=word, skip=skip, limit=limit),
            remote_fetcher=partial(self.remote.search_illust, word=word),
            cache_updater=lambda content: self.cache.update_search_illust(
                word, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def search_user(self, word: str, *, skip: int = 0, limit: int = 0) -> typing.List[User]:
        return await self._mediator.get(
            identifier=(1, word),
            cache_loader=partial(self.cache.search_user,
                                 word=word, skip=skip, limit=limit),
            remote_fetcher=partial(self.remote.search_user, word=word),
            cache_updater=lambda content: self.cache.update_search_user(
                word, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def user_illusts(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        return await self._mediator.get(
            identifier=(2, user_id),
            cache_loader=partial(self.cache.user_illusts,
                                 user_id=user_id, skip=skip, limit=limit),
            remote_fetcher=partial(self.remote.user_illusts, user_id=user_id),
            cache_updater=lambda content: self.cache.update_user_illusts(
                user_id, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def user_bookmarks(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        return await self._mediator.get(
            identifier=(3, user_id),
            cache_loader=partial(self.cache.user_bookmarks,
                                 user_id=user_id, skip=skip, limit=limit),
            remote_fetcher=partial(
                self.remote.user_bookmarks, user_id=user_id),
            cache_updater=lambda content: self.cache.update_user_bookmarks(
                user_id, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def recommended_illusts(self, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        return await self._mediator.get(
            identifier=(4,),
            cache_loader=partial(
                self.cache.recommended_illusts, skip=skip, limit=limit),
            remote_fetcher=self.remote.recommended_illusts,
            cache_updater=self.cache.update_recommended_illusts,
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def related_illusts(self, illust_id: int, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        return await self._mediator.get(
            identifier=(8, illust_id),
            cache_loader=partial(
                self.cache.related_illusts, illust_id=illust_id, skip=skip, limit=limit),
            remote_fetcher=partial(
                self.remote.related_illusts, illust_id=illust_id),
            cache_updater=lambda content: self.cache.update_related_illusts(
                illust_id, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def illust_ranking(self, mode: RankingMode = RankingMode.day,
                             *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        return await self._mediator.get(
            identifier=(5, mode),
            cache_loader=partial(
                self.cache.illust_ranking, mode=mode, skip=skip, limit=limit),
            remote_fetcher=partial(
                self.remote.illust_ranking, mode=mode),
            cache_updater=lambda content: self.cache.update_illust_ranking(
                mode, content),
            hook_on_fetch=lambda result: do_skip_and_limit(
                result, skip, limit),
            timeout=self._conf.pixiv_query_timeout
        )

    async def image(self, illust: Illust) -> bytes:
        return await self._mediator.get(
            identifier=(7, illust.id),
            cache_loader=partial(self.cache.image, illust=illust),
            remote_fetcher=partial(self.remote.image, illust=illust),
            cache_updater=lambda content: self.cache.update_image(
                illust, content),
            timeout=self._conf.pixiv_query_timeout
        )


__all__ = ('PixivRepo',)

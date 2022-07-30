from datetime import datetime, timedelta
from functools import partial
from typing import List, Tuple, AsyncGenerator, Optional

from nonebot import logger

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


@context.root.register_singleton()
class PixivRepo(AbstractPixivRepo):
    _conf: Config = context.require(Config)

    def __init__(self):
        self._mediator: Mediator = None
        self.remote = context.require(RemotePixivRepo)
        self.cache = context.require(LocalPixivRepo)

        on_startup(self.start, replay=True)
        on_shutdown(self.shutdown)

    async def start(self):
        await self.remote.start()
        self._mediator = Mediator(self._conf.pixiv_simultaneous_query)

    async def shutdown(self):
        await self.remote.shutdown()

    async def invalidate_cache(self):
        await self.cache.invalidate_cache()

    async def illust_detail(self, illust_id: int) -> Illust:
        logger.info(f"[repo] illust_detail {illust_id}")
        return await self._mediator.mixin(
            identifier=(ILLUST_DETAIL, illust_id),
            cache_loader=partial(self.cache.illust_detail, illust_id=illust_id),
            remote_fetcher=partial(self.remote.illust_detail, illust_id=illust_id),
            cache_updater=self.cache.update_illust_detail
        )

    async def user_detail(self, user_id: int) -> User:
        logger.info(f"[repo] user_detail {user_id}")
        return await self._mediator.mixin(
            identifier=(USER_DETAIL, user_id),
            cache_loader=partial(self.cache.user_detail, user_id=user_id),
            remote_fetcher=partial(self.remote.user_detail, user_id=user_id),
            cache_updater=self.cache.update_user_detail
        )

    def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] search_illust {word}")
        return self._mediator.mixin_async_generator(
            identifier=(SEARCH_ILLUST, word),
            cache_loader=partial(self.cache.search_illust, word=word),
            remote_fetcher=partial(self.remote.search_illust, word=word),
            cache_updater=lambda content: self.cache.update_search_illust(word, content),
        )

    def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.info(f"[repo] search_user {word}")
        return self._mediator.mixin_async_generator(
            identifier=(SEARCH_USER, word),
            cache_loader=partial(self.cache.search_user, word=word),
            remote_fetcher=partial(self.remote.search_user, word=word),
            cache_updater=lambda content: self.cache.update_search_user(word, content),
        )

    def user_illusts(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_illusts {user_id}")
        return self._mediator.mixin_async_generator(
            identifier=(USER_ILLUSTS, user_id),
            cache_loader=partial(self.cache.user_illusts, user_id=user_id),
            remote_fetcher=partial(self.remote.user_illusts, user_id=user_id),
            cache_updater=lambda content: self.cache.update_user_illusts(user_id, content),
        )

    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] user_bookmarks {user_id}")

        # if cache expired, pick new bookmarks from remote
        update_time = await self.cache.user_bookmarks_update_time(user_id)
        if not update_time \
                or datetime.now() - update_time >= timedelta(seconds=self._conf.pixiv_user_bookmarks_cache_expires_in):
            buffer = []
            async for illust in self.remote.user_bookmarks(user_id):
                buffer.append(illust)
                if len(buffer) >= 20:
                    exists = await self.cache.user_bookmarks_exists(user_id, [x.id for x in buffer])
                    await self.cache.update_user_bookmarks(user_id, buffer, append=True)

                    if exists:
                        break

                    buffer = []

        async for x in self.cache.user_bookmarks(user_id):
            yield x

    def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] recommended_illusts")
        return self._mediator.mixin_async_generator(
            identifier=(RECOMMENDED_ILLUSTS,),
            cache_loader=partial(self.cache.recommended_illusts),
            remote_fetcher=self.remote.recommended_illusts,
            cache_updater=self.cache.update_recommended_illusts,
        )

    def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.info(f"[repo] related_illusts {illust_id}")
        return self._mediator.mixin_async_generator(
            identifier=(RELATED_ILLUSTS, illust_id),
            cache_loader=partial(self.cache.related_illusts, illust_id=illust_id),
            remote_fetcher=partial(self.remote.related_illusts, illust_id=illust_id),
            cache_updater=lambda content: self.cache.update_related_illusts(illust_id, content),
        )

    async def illust_ranking(self, mode: RankingMode, range: Optional[Tuple[int, int]] = None) -> List[LazyIllust]:
        logger.info(f"[repo] illust_ranking {mode} {range}")
        return await self._mediator.mixin(
            identifier=(ILLUST_RANKING, mode),
            cache_loader=partial(self.cache.illust_ranking, mode=mode, range=range),
            remote_fetcher=partial(self.remote.illust_ranking, mode=mode),
            cache_updater=lambda content: self.cache.update_illust_ranking(mode, content),
            hook_on_fetch=lambda result: do_skip_and_limit(result, range[0] - 1, range[1] - range[0] + 1)
        )

    async def image(self, illust: Illust) -> bytes:
        logger.info(f"[repo] image {illust.id}")
        return await self._mediator.mixin(
            identifier=(IMAGE, illust.id),
            cache_loader=partial(self.cache.image, illust=illust),
            remote_fetcher=partial(self.remote.image, illust=illust),
            cache_updater=lambda content: self.cache.update_image(illust, content)
        )


__all__ = ('PixivRepo',)

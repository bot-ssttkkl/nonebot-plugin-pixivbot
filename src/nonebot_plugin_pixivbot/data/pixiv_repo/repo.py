from typing import AsyncGenerator

from nonebot import logger

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .abstract_repo import AbstractPixivRepo, PixivRepoMetadata
from .enums import *
from .lazy_illust import LazyIllust
from .local_repo import LocalPixivRepo
from .pkg_context import context
from .shared_agen import PixivSharedAsyncGeneratorManager


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

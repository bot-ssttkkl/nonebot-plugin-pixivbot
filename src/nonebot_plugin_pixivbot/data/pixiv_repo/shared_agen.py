from abc import ABC, abstractmethod
from asyncio import Lock
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from functools import partial
from inspect import isawaitable
from types import TracebackType
from typing import Any, Awaitable, Generic, TypeVar, Callable, Union, AsyncGenerator, List, Type, Optional, Dict, Tuple

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from nonebot_plugin_pixivbot.utils.expires_lru_dict import ExpiresLruDict
from . import LazyIllust
from .abstract_repo import PixivRepoMetadata
from .enums import *
from .local_repo import LocalPixivRepo
from .mediator import mediate_single, mediate_many, mediate_append
from .pkg_context import context
from .remote_repo import RemotePixivRepo

T_ID = TypeVar("T_ID")
T_ITEM = TypeVar("T_ITEM")


class SharedAsyncGeneratorContextManager(AbstractContextManager, Generic[T_ITEM]):
    def __init__(self, origin: AsyncGenerator[T_ITEM, None],
                 on_each: Callable[[T_ITEM], Union[None, Awaitable[None]]],
                 on_stop: Callable[[List[T_ITEM]],
                                   Union[None, Awaitable[None]]],
                 on_consumers_changed: Callable[["SharedAsyncGeneratorContextManager", int], None]):
        super().__init__()
        self._origin = origin
        self._stopped = False  # whether origin has raised a StopIteration
        self._got_items = []  # items got from origin, used to replay
        self._got = 0  # count of items got from origin
        self._mutex = Lock()  # to solve race
        self._consumers = 0  # count of consumer
        self._on_each = on_each  # callback on origin yields
        self._on_stop = on_stop  # callback on origin stops
        self._on_consumers_changed = on_consumers_changed  # callback on a consumer enters or exits

    @property
    def consumers(self) -> int:
        return self._consumers

    async def _generator_factory(self) -> AsyncGenerator[T_ITEM, None]:
        cur = 0
        while True:
            if cur < self._got:
                yield self._got_items[cur]
                cur += 1
            else:
                if self._stopped:
                    break

                async with self._mutex:
                    if self._stopped:
                        break

                    try:
                        if cur == self._got:
                            new_data = await self._origin.__anext__()
                            await self._on_each(new_data)
                            self._got_items.append(new_data)
                            self._got += 1
                        yield self._got_items[cur]
                        cur += 1
                    except StopAsyncIteration:
                        self._stopped = True
                        x = self._on_stop(self._got_items)
                        if isawaitable(x):
                            await x

    def __enter__(self) -> AsyncGenerator[T_ITEM, None]:
        self._consumers += 1
        self._on_consumers_changed(self, self._consumers)
        return self._generator_factory()

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self._consumers -= 1
        self._on_consumers_changed(self, self._consumers)

    # def close(self):
    #     self._stopped = True
    #     self._origin.athrow(GeneratorExit)


class SharedAsyncGeneratorManager(ABC, Generic[T_ID]):
    def __init__(self):
        self._ctx_mgr = {}
        self._paused_ctx_mgr = ExpiresLruDict(1024)
        self._expires_time: Dict[T_ID, datetime] = {}

    @abstractmethod
    def agen_factory(self, identifier: T_ID, *args, **kwargs) -> AsyncGenerator[T_ITEM, None]:
        raise NotImplementedError()

    def on_agen_next(self, identifier: T_ID, item: T_ITEM) -> Union[None, Awaitable[None]]:
        pass

    def on_agen_stop(self, identifier: T_ID, items: List[T_ITEM]) -> Union[None, Awaitable[None]]:
        pass

    def on_consumers_changed(self, identifier: T_ID,
                             ctx_mgr: SharedAsyncGeneratorContextManager[T_ITEM],
                             consumers: int):
        if identifier in self._paused_ctx_mgr and consumers > 0:
            logger.debug(f"[agen_manager] {identifier} re-started")
            del self._paused_ctx_mgr[identifier]
            self._ctx_mgr[identifier] = ctx_mgr
        elif identifier in self._ctx_mgr and consumers == 0:
            del self._ctx_mgr[identifier]
            if identifier in self._expires_time:
                logger.debug(f"[agen_manager] {identifier} paused")
                self._paused_ctx_mgr.add(identifier, ctx_mgr, self._expires_time[identifier])
            else:
                logger.debug(f"[agen_manager] {identifier} stopped")

    def get_expires_time(self, identifier: T_ID) -> Optional[datetime]:
        return self._expires_time.get(identifier, None)

    def set_expires_time(self, identifier: T_ID, expires_time: datetime):
        if identifier not in self._expires_time:
            self._expires_time[identifier] = expires_time
            logger.debug(f"[agen_manager] {identifier} will expire at {expires_time}")
        elif self._expires_time[identifier] != expires_time:
            raise RuntimeError(f"{identifier} expires time already set")

    def get(self, identifier: Any, *args, **kwargs) \
            -> SharedAsyncGeneratorContextManager[T_ITEM]:
        if identifier in self._paused_ctx_mgr:
            return self._paused_ctx_mgr[identifier]
        elif identifier in self._ctx_mgr:
            return self._ctx_mgr[identifier]
        else:
            origin = self.agen_factory(identifier, *args, **kwargs)
            self._ctx_mgr[identifier] = SharedAsyncGeneratorContextManager(
                origin=origin,
                on_each=lambda item: self.on_agen_next(identifier, item),
                on_stop=lambda items: self.on_agen_stop(identifier, items),
                on_consumers_changed=lambda ctx_mgr, consumers: self.on_consumers_changed(
                    identifier, ctx_mgr, consumers)
            )
            return self._ctx_mgr[identifier]


@context.inject
@context.register_singleton()
class PixivSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[Tuple[int, Any]]):
    conf: Config
    local: LocalPixivRepo
    remote: RemotePixivRepo

    def calc_expires_time(self, identifier: T_ID, update_time: datetime) -> datetime:
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

    async def on_agen_next(self, identifier: T_ID, item: T_ITEM):
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

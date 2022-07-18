import typing
from abc import ABC, abstractmethod

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .lazy_illust import LazyIllust


class AbstractPixivRepo(ABC):
    @abstractmethod
    async def illust_detail(self, illust_id: int) -> Illust:
        raise NotImplementedError()

    @abstractmethod
    async def user_detail(self, user_id: int) -> User:
        raise NotImplementedError()

    @abstractmethod
    async def search_illust(self, word: str, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def search_user(self, word: str, *, skip: int = 0, limit: int = 0) -> typing.List[User]:
        raise NotImplementedError()

    @abstractmethod
    async def user_illusts(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def user_bookmarks(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def recommended_illusts(self, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def related_illusts(self, illust_id: int, *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def illust_ranking(self, mode: RankingMode = RankingMode.day,
                             *, skip: int = 0, limit: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def image(self, illust: Illust) -> bytes:
        raise NotImplementedError()

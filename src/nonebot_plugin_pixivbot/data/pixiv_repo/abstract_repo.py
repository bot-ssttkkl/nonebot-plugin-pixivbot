from abc import ABC, abstractmethod
from typing import Tuple, AsyncGenerator, List

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
    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        raise NotImplementedError()

    @abstractmethod
    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        raise NotImplementedError()

    @abstractmethod
    async def user_illusts(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        raise NotImplementedError()

    @abstractmethod
    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        raise NotImplementedError()

    @abstractmethod
    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        raise NotImplementedError()

    @abstractmethod
    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        raise NotImplementedError()

    @abstractmethod
    async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def image(self, illust: Illust) -> bytes:
        raise NotImplementedError()


__all__ = ("AbstractPixivRepo", )

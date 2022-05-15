from abc import ABC, abstractmethod
import typing

from ...model import Illust, User
from .lazy_illust import LazyIllust


class AbstractDataSource(ABC):
    @abstractmethod
    async def illust_detail(self, illust_id: int) -> Illust:
        raise NotImplementedError()

    @abstractmethod
    async def search_illust(self, word: str) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def search_user(self, word: str) -> typing.List[User]:
        raise NotImplementedError()

    @abstractmethod
    async def user_illusts(self, user_id: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def user_bookmarks(self, user_id: int = 0) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def recommended_illusts(self) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def related_illusts(self, illust_id: int) -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def illust_ranking(self, mode: str = 'day') -> typing.List[LazyIllust]:
        raise NotImplementedError()

    @abstractmethod
    async def image(self, illust: Illust) -> bytes:
        raise NotImplementedError()

from abc import ABC, abstractmethod
from typing import Union, AsyncGenerator

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .lazy_illust import LazyIllust
from .models import PixivRepoMetadata


class AbstractPixivRepo(ABC):
    @abstractmethod
    def illust_detail(self, illust_id: int) -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def user_detail(self, user_id: int) -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def search_illust(self, word: str) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def search_user(self, word: str) -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def user_illusts(self, user_id: int) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def recommended_illusts(self) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def related_illusts(self, illust_id: int) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def illust_ranking(self, mode: Union[str, RankingMode]) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        raise NotImplementedError()

    @abstractmethod
    def image(self, illust: Illust) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        raise NotImplementedError()


__all__ = ("AbstractPixivRepo",)

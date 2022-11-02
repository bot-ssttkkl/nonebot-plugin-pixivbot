from typing import Union, AsyncGenerator, Protocol

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from .lazy_illust import LazyIllust
from .models import PixivRepoMetadata


class PixivRepo(Protocol):
    def illust_detail(self, illust_id: int) -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        ...

    def user_detail(self, user_id: int) -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        ...

    def search_illust(self, word: str) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def search_user(self, word: str) -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        ...

    def user_illusts(self, user_id: int) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def recommended_illusts(self) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def related_illusts(self, illust_id: int) -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def illust_ranking(self, mode: Union[str, RankingMode]) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        ...

    def image(self, illust: Illust) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        ...


__all__ = ("PixivRepo",)

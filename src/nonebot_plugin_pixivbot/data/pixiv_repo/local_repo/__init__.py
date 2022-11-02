from typing import Protocol, List, Union

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.pixiv_repo import LazyIllust
from nonebot_plugin_pixivbot.data.pixiv_repo.models import PixivRepoMetadata
from nonebot_plugin_pixivbot.enums import RankingMode, DataSourceType
from nonebot_plugin_pixivbot.model import Illust, User


class LocalPixivRepo(Protocol):
    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata):
        ...

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata):
        ...

    async def invalidate_search_illust(self, word: str):
        ...

    async def append_search_illust(self, word: str,
                                   content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_search_user(self, word: str):
        ...

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_user_illusts(self, user_id: int):
        ...

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_user_bookmarks(self, user_id: int):
        ...

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_recommended_illusts(self):
        ...

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_related_illusts(self, illust_id: int):
        ...

    async def append_related_illusts(self, illust_id: int,
                                     content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        ...

    async def invalidate_illust_ranking(self, mode: RankingMode):
        ...

    async def append_illust_ranking(self, mode: RankingMode,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        ...

    async def update_image(self, illust_id: int, content: bytes,
                           metadata: PixivRepoMetadata):
        ...

    async def invalidate_all(self):
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoPixivRepo

    context.bind(LocalPixivRepo, MongoPixivRepo)
else:
    from .sql import SqlPixivRepo

    context.bind(LocalPixivRepo, SqlPixivRepo)

__all__ = ("LocalPixivRepo",)

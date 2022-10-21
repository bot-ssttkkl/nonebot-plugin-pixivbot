from datetime import datetime, timezone
from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.source import MongoDataSource
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import Illust, User

conf = context.require(Config)


class PixivRepoMetadata(BaseModel):
    update_time: datetime = datetime.now(timezone.utc)
    pages: Optional[int]
    next_qs: Optional[dict]

    def __str__(self):
        return '(' + ', '.join(map(lambda kv: kv[0] + '=' + str(kv[1]), self.dict(exclude_none=True).items())) + ')'


class PixivRepoCache(Document):
    metadata: PixivRepoMetadata


class IllustSetCache(PixivRepoCache):
    illust_id: List[int]


class UserSetCache(PixivRepoCache):
    user_id: List[int]


class DownloadCache(PixivRepoCache):
    illust_id: int
    content: bytes

    class Settings:
        name = "download_cache"
        indexes = [
            IndexModel([("illust_id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_download_cache_expires_in)
        ]


class IllustDetailCache(PixivRepoCache):
    illust: Illust

    class Settings:
        name = "illust_detail_cache"
        indexes = [
            IndexModel([("illust.id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_illust_detail_cache_expires_in)
        ]


class IllustRankingCache(IllustSetCache):
    mode: RankingMode

    class Settings:
        name = "illust_ranking_cache"
        indexes = [
            IndexModel([("mode", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_illust_ranking_cache_expires_in)
        ]


class OtherIllustCache(IllustSetCache):
    type: str

    class Settings:
        name = "other_cache"
        indexes = [
            IndexModel([("type", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_other_cache_expires_in)
        ]


class RelatedIllustsCache(IllustSetCache):
    original_illust_id: int

    class Settings:
        name = "related_illusts_cache"
        indexes = [
            IndexModel([("original_illust_id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_related_illusts_cache_expires_in)
        ]


class SearchIllustCache(IllustSetCache):
    word: str

    class Settings:
        name = "search_illust_cache"
        indexes = [
            IndexModel([("word", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_search_illust_cache_delete_in)
        ]


class SearchUserCache(UserSetCache):
    word: str
    user_id: List[int]

    class Settings:
        name = "search_user_cache"
        indexes = [
            IndexModel([("word", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_search_user_cache_delete_in)
        ]


class UserBookmarksCache(IllustSetCache):
    user_id: int

    class Settings:
        name = "user_bookmarks_cache"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_user_bookmarks_cache_delete_in)
        ]


class UserDetailCache(PixivRepoCache):
    user: User

    class Settings:
        name = "user_detail_cache"
        indexes = [
            IndexModel([("user.id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_user_detail_cache_expires_in)
        ]


class UserIllustsCache(IllustSetCache):
    user_id: int

    class Settings:
        name = "user_illusts_cache"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("update_time", 1)], expireAfterSeconds=conf.pixiv_user_illusts_cache_delete_in)
        ]


context.require(MongoDataSource).document_models.extend([
    DownloadCache, IllustDetailCache, IllustRankingCache, OtherIllustCache,
    RelatedIllustsCache, SearchIllustCache, SearchUserCache,
    UserBookmarksCache, UserDetailCache, UserIllustsCache
])

__all__ = ("PixivRepoMetadata", "PixivRepoCache", "IllustSetCache",
           "DownloadCache", "IllustDetailCache", "IllustRankingCache", "OtherIllustCache",
           "RelatedIllustsCache", "SearchIllustCache", "SearchUserCache",
           "UserBookmarksCache", "UserDetailCache", "UserIllustsCache")

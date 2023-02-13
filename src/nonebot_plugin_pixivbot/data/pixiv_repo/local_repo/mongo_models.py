from typing import List

from beanie.odm.interfaces.aggregate import AggregateInterface
from beanie.odm.interfaces.find import FindInterface
from beanie.odm.interfaces.getters import OtherGettersInterface
from pydantic import BaseModel
from pymongo import IndexModel

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.pixiv_repo.models import PixivRepoMetadata
from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Illust, User
from ...source.mongo import MongoDocument

conf = context.require(Config)


class PixivRepoCache(BaseModel,
                     FindInterface,
                     AggregateInterface,
                     OtherGettersInterface):
    metadata: PixivRepoMetadata


class IllustSetCache(PixivRepoCache):
    illust_id: List[int]


class UserSetCache(PixivRepoCache):
    user_id: List[int]


class DownloadCache(MongoDocument, PixivRepoCache):
    illust_id: int
    page: int
    content: bytes

    class Settings:
        name = "download_cache"
        indexes = [
            IndexModel([("illust_id", 1), ("page", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_download_cache_expires_in)
        ]


class IllustDetailCache(MongoDocument, PixivRepoCache):
    illust: Illust

    class Settings:
        name = "illust_detail_cache"
        indexes = [
            IndexModel([("illust.id", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_illust_detail_cache_expires_in)
        ]


class IllustRankingCache(MongoDocument, IllustSetCache):
    mode: RankingMode

    class Settings:
        name = "illust_ranking_cache"
        indexes = [
            IndexModel([("mode", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_illust_ranking_cache_expires_in)
        ]


class OtherIllustCache(MongoDocument, IllustSetCache):
    type: str

    class Settings:
        name = "other_cache"
        indexes = [
            IndexModel([("type", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_other_cache_expires_in)
        ]


class RelatedIllustsCache(MongoDocument, IllustSetCache):
    original_illust_id: int

    class Settings:
        name = "related_illusts_cache"
        indexes = [
            IndexModel([("original_illust_id", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_related_illusts_cache_expires_in)
        ]


class SearchIllustCache(MongoDocument, IllustSetCache):
    word: str

    class Settings:
        name = "search_illust_cache"
        indexes = [
            IndexModel([("word", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_search_illust_cache_delete_in)
        ]


class SearchUserCache(MongoDocument, UserSetCache):
    word: str

    class Settings:
        name = "search_user_cache"
        indexes = [
            IndexModel([("word", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_search_user_cache_delete_in)
        ]


class UserBookmarksCache(MongoDocument, IllustSetCache):
    user_id: int

    class Settings:
        name = "user_bookmarks_cache"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_user_bookmarks_cache_delete_in)
        ]


class UserDetailCache(MongoDocument, PixivRepoCache):
    user: User

    class Settings:
        name = "user_detail_cache"
        indexes = [
            IndexModel([("user.id", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_user_detail_cache_expires_in)
        ]


class UserIllustsCache(MongoDocument, IllustSetCache):
    user_id: int

    class Settings:
        name = "user_illusts_cache"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("metadata.update_time", 1)], expireAfterSeconds=conf.pixiv_user_illusts_cache_delete_in)
        ]


__all__ = ("PixivRepoCache", "IllustSetCache",
           "DownloadCache", "IllustDetailCache", "IllustRankingCache", "OtherIllustCache",
           "RelatedIllustsCache", "SearchIllustCache", "SearchUserCache",
           "UserBookmarksCache", "UserDetailCache", "UserIllustsCache")

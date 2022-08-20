from enum import Enum


class PixivResType(Enum):
    SEARCH_ILLUST = 0
    SEARCH_USER = 1
    USER_ILLUSTS = 2
    USER_BOOKMARKS = 3
    RECOMMENDED_ILLUSTS = 4
    ILLUST_RANKING = 5
    ILLUST_DETAIL = 6
    IMAGE = 7
    RELATED_ILLUSTS = 8
    USER_DETAIL = 9


class CacheStrategy(Enum):
    NORMAL = 0
    FORCE_EXPIRATION = 1

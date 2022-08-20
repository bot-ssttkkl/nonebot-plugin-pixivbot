from enum import Enum

__all__ = ("BlockAction", "DownloadQuantity", "RandomIllustMethod", "RankingMode",)


class BlockAction(Enum):
    no_image = 'no_image'
    completely_block = 'completely_block'
    no_reply = 'no_reply'


class DownloadQuantity(Enum):
    original = 'original'
    square_medium = 'square_medium'
    medium = 'medium'
    large = 'large'


class RandomIllustMethod(Enum):
    uniform = 'uniform'
    bookmark_proportion = 'bookmark_proportion'
    view_proportion = 'view_proportion'
    timedelta_proportion = 'timedelta_proportion'


class RankingMode(Enum):
    day = 'day'
    week = 'week'
    month = 'month'
    day_male = 'day_male'
    day_female = 'day_female'
    week_original = 'week_original'
    week_rookie = 'week_rookie'
    day_manga = 'day_manga'

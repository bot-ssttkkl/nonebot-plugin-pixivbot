import typing

from pydantic import *

from .Illust import Illust
from .PixivError import PixivError


class PixivResult(BaseModel):
    error: typing.Optional[PixivError] = None


class IllustResult(PixivResult):
    illust: typing.Optional[Illust] = None


class IllustListResult(PixivResult):
    illusts: typing.List[Illust]


class PagedIllustListResult(IllustListResult):
    next_url: typing.Optional[str] = None

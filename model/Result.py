import typing

from pydantic import *

from .Illust import Illust
from .Error import Error


class PixivResult(BaseModel):
    error: typing.Optional[Error] = None


class IllustResult(PixivResult):
    illust: typing.Optional[Illust] = None


class IllustListResult(PixivResult):
    illusts: typing.List[Illust]


class PagedIllustListResult(IllustListResult):
    next_url: typing.Optional[str] = None

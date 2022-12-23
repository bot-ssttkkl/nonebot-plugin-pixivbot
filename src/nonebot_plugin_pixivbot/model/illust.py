import datetime
import typing

from pydantic import *

from .tag import Tag
from .user import User


class Illust(BaseModel):
    class ImageUrls(BaseModel):
        square_medium: str
        medium: str
        large: str

    class MetaSinglePage(BaseModel):
        original_image_url: typing.Optional[str] = None

    class MetaPage(BaseModel):
        class ImageUrls(BaseModel):
            square_medium: str
            medium: str
            large: str
            original: str

        image_urls: ImageUrls

    id: int
    title: str
    type: str
    image_urls: ImageUrls
    caption: str
    user: User
    tags: typing.List[Tag]
    create_date: datetime.datetime
    page_count: int
    meta_single_page: MetaSinglePage
    meta_pages: typing.List[MetaPage]
    total_view: int
    total_bookmarks: int

    def has_tag(self, tag: typing.Union[str, Tag]) -> bool:
        if isinstance(tag, Tag):
            for x in self.tags:
                if x == tag:
                    return True
            return False
        else:
            for x in self.tags:
                if x.name == tag or x.translated_name == tag:
                    return True
            return False

    def has_tags(self, tags: typing.List[typing.Union[str, Tag]]) -> bool:
        for tag in tags:
            if self.has_tag(tag):
                return True
        return False

    def page_image_url(self, page: int) -> str:
        if len(self.meta_pages) > 0:
            return self.meta_pages[page].image_urls.original
        else:
            if page == 0:
                return self.meta_single_page.original_image_url
            else:
                raise IndexError(page)


__all__ = ("Illust",)

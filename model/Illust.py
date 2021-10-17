import datetime
import typing

from pydantic import *


class Illust(BaseModel):
    class ImageUrls(BaseModel):
        square_medium: str
        medium: str
        large: str

    class User(BaseModel):
        class ProfileImageUrls(BaseModel):
            medium: str

        id: int
        name: str
        account: str
        profile_image_urls: ProfileImageUrls
        is_followed: bool

    class Tag(BaseModel):
        name: str
        translated_name: typing.Optional[str] = None

    class Series(BaseModel):
        id: int
        title: str

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
    restrict: int
    user: User
    tags: typing.List[Tag]
    tools: typing.List[str]
    create_date: datetime.datetime  # time
    page_count: int
    width: int
    height: int
    sanity_level: int
    x_restrict: int
    series: typing.Optional[Series] = None
    meta_single_page: MetaSinglePage
    meta_pages: typing.List[MetaPage]
    total_view: int
    total_bookmarks: int
    is_bookmarked: bool
    visible: bool
    is_muted: bool
    total_comments: typing.Optional[int] = None

    def has_tag(self, tag: typing.Union[str, Tag]) -> bool:
        if isinstance(tag, self.Tag):
            for x in self.tags:
                if x == tag:
                    return True
            return False
        else:
            for x in self.tags:
                if x.name == tag or x.translated_name == tag:
                    return True
            return False

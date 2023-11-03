from datetime import datetime
from typing import Optional, List

from nonebot_plugin_orm import Model
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, relationship, Mapped

from ...sql_common import BLOB, JSON, UTCDateTime
from ...sql_common.pydantic import PydanticModel
from ....model import Illust, User
from ....utils.json import dumps_default


class DownloadCache(Model):
    __tablename__ = "pixivbot_download_cache"

    illust_id: Mapped[int] = mapped_column(primary_key=True)
    page: Mapped[int] = mapped_column(primary_key=True, default=0)
    content: Mapped[bytes] = mapped_column(BLOB)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class IllustDetailCache(Model):
    __tablename__ = "pixivbot_illust_detail_cache"

    illust_id: Mapped[int] = mapped_column(primary_key=True)
    illust: Mapped[Illust] = mapped_column(PydanticModel(Illust, dumps_default=dumps_default))

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class UserDetailCache(Model):
    __tablename__ = "pixivbot_user_detail_cache"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[User] = mapped_column(PydanticModel(User, dumps_default=dumps_default))

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class IllustSetCache(Model):
    __tablename__ = "pixivbot_illust_set_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cache_type: Mapped[str]
    key: Mapped[dict] = mapped_column(JSON)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    pages: Mapped[Optional[int]]
    next_qs: Mapped[Optional[dict]] = mapped_column(JSON)

    illust_id: Mapped[List["IllustSetCacheIllust"]] = relationship(foreign_keys="IllustSetCacheIllust.cache_id",
                                                                   cascade="save-update, delete",
                                                                   passive_deletes=True)

    size: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        UniqueConstraint('cache_type', 'key',
                         name="uq_pixivbot_illust_set_cache_cache_type_key"),
    )


class IllustSetCacheIllust(Model):
    __tablename__ = "pixivbot_illust_set_cache_illust"

    cache_id: Mapped[int] = mapped_column(ForeignKey("pixivbot_illust_set_cache.id", ondelete="cascade"),
                                          primary_key=True)
    illust_id: Mapped[int] = mapped_column(primary_key=True)
    rank: Mapped[int] = mapped_column(default=0)


class UserSetCache(Model):
    __tablename__ = "pixivbot_user_set_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cache_type: Mapped[str]
    key: Mapped[dict] = mapped_column(JSON)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    pages: Mapped[Optional[int]]
    next_qs: Mapped[Optional[dict]] = mapped_column(JSON)

    illust_id: Mapped[List["UserSetCacheUser"]] = relationship(foreign_keys="UserSetCacheUser.cache_id",
                                                               cascade="save-update, delete",
                                                               passive_deletes=True)

    __table_args__ = (
        UniqueConstraint('cache_type', 'key',
                         name="uq_pixivbot_user_set_cache_cache_type_key"),
    )


class UserSetCacheUser(Model):
    __tablename__ = "pixivbot_user_set_cache_user"

    cache_id: Mapped[int] = mapped_column(ForeignKey("pixivbot_user_set_cache.id", ondelete="cascade"),
                                          primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True)

from datetime import datetime
from typing import Optional, List

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, relationship, Mapped

from ...source.sql import DataSource
from ...utils.sql import BLOB, JSON, UTCDateTime


@DataSource.registry.mapped
class DownloadCache:
    __tablename__ = "download_cache"

    illust_id: Mapped[int] = mapped_column(primary_key=True)
    page: Mapped[int] = mapped_column(primary_key=True, default=0)
    content: Mapped[bytes] = mapped_column(BLOB)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


@DataSource.registry.mapped
class IllustDetailCache:
    __tablename__ = "illust_detail_cache"

    illust_id: Mapped[int] = mapped_column(primary_key=True)
    illust: Mapped[dict] = mapped_column(JSON)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


@DataSource.registry.mapped
class UserDetailCache:
    __tablename__ = "user_detail_cache"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[dict] = mapped_column(JSON)

    update_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


@DataSource.registry.mapped
class IllustSetCache:
    __tablename__ = "illust_set_cache"

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
        UniqueConstraint('cache_type', 'key'),
    )


@DataSource.registry.mapped
class IllustSetCacheIllust:
    __tablename__ = "illust_set_cache_illust"

    cache_id: Mapped[int] = mapped_column(ForeignKey("illust_set_cache.id", ondelete="cascade"), primary_key=True)
    illust_id: Mapped[int] = mapped_column(primary_key=True)
    rank: Mapped[int] = mapped_column(default=0)


@DataSource.registry.mapped
class UserSetCache:
    __tablename__ = "user_set_cache"

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
        UniqueConstraint('cache_type', 'key'),
    )


@DataSource.registry.mapped
class UserSetCacheUser:
    __tablename__ = "user_set_cache_user"

    cache_id: Mapped[int] = mapped_column(ForeignKey("user_set_cache.id", ondelete="cascade"), primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True)

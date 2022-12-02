from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.sql import BLOB, JSON, UTCDateTime


@context.require(SqlDataSource).registry.mapped
class DownloadCache:
    __tablename__ = "download_cache"

    illust_id: int = Column(Integer, primary_key=True, nullable=False)
    content: bytes = Column(BLOB, nullable=False)

    update_time: datetime = Column(UTCDateTime, nullable=False, index=True)


@context.require(SqlDataSource).registry.mapped
class IllustDetailCache:
    __tablename__ = "illust_detail_cache"

    illust_id: int = Column(Integer, primary_key=True, nullable=False)
    illust: dict = Column(JSON, nullable=False)

    update_time: datetime = Column(UTCDateTime, nullable=False, index=True)


@context.require(SqlDataSource).registry.mapped
class UserDetailCache:
    __tablename__ = "user_detail_cache"

    user_id: int = Column(Integer, primary_key=True, nullable=False)
    user: dict = Column(JSON, nullable=False)

    update_time: datetime = Column(UTCDateTime, nullable=False, index=True)


@context.require(SqlDataSource).registry.mapped
class IllustSetCache:
    __tablename__ = "illust_set_cache"

    id: int = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    cache_type: str = Column(String, nullable=False)
    key: dict = Column(JSON, nullable=False)

    update_time: datetime = Column(UTCDateTime, nullable=False, index=True)
    pages: Optional[int] = Column(Integer)
    next_qs: Optional[dict] = Column(JSON)

    illust_id: List["IllustSetCacheIllust"] = relationship("IllustSetCacheIllust",
                                                           foreign_keys="IllustSetCacheIllust.cache_id",
                                                           cascade="save-update, delete",
                                                           passive_deletes=True)

    size: int = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('cache_type', 'key'),
    )


@context.require(SqlDataSource).registry.mapped
class IllustSetCacheIllust:
    __tablename__ = "illust_set_cache_illust"

    cache_id: int = Column(Integer, ForeignKey("illust_set_cache.id", ondelete="cascade"), primary_key=True, nullable=False)
    illust_id: int = Column(Integer, primary_key=True, nullable=False)
    rank: int = Column(Integer, nullable=False, default=0)


@context.require(SqlDataSource).registry.mapped
class UserSetCache:
    __tablename__ = "user_set_cache"

    id: int = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    cache_type: str = Column(String, nullable=False)
    key: dict = Column(JSON, nullable=False)

    update_time: datetime = Column(UTCDateTime, nullable=False, index=True)
    pages: Optional[int] = Column(Integer)
    next_qs: Optional[dict] = Column(JSON)

    illust_id: List["UserSetCacheUser"] = relationship("UserSetCacheUser",
                                                       foreign_keys="UserSetCacheUser.cache_id",
                                                       cascade="save-update, delete",
                                                       passive_deletes=True)

    __table_args__ = (
        UniqueConstraint('cache_type', 'key'),
    )


@context.require(SqlDataSource).registry.mapped
class UserSetCacheUser:
    __tablename__ = "user_set_cache_user"

    cache_id: int = Column(Integer, ForeignKey("user_set_cache.id", ondelete="cascade"), primary_key=True, nullable=False)
    user_id: int = Column(Integer, primary_key=True, nullable=False)

from sqlalchemy import Column, String

from ..sql import DataSource


@DataSource.registry.mapped
class MetaInfo:
    __tablename__ = "meta_info"

    key: str = Column("key", String, primary_key=True)
    value: str = Column("value", String, nullable=False)

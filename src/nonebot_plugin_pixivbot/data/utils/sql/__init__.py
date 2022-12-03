from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config

dialect = context.require(Config).pixiv_sql_dialect
if dialect == 'sqlite':
    from sqlalchemy.dialects.sqlite import insert as _insert
    from sqlalchemy.dialects.sqlite import JSON as _JSON
    from sqlalchemy.dialects.sqlite import BLOB as _BLOB
elif dialect == 'postgresql':
    from sqlalchemy.dialects.postgresql import insert as _insert
    from sqlalchemy.dialects.postgresql import JSONB as _JSON
    from sqlalchemy.dialects.postgresql import BYTEA as _BLOB
else:
    raise RuntimeError(f"不支持使用此SQL数据库：{dialect}")

insert = _insert
JSON = _JSON
BLOB = _BLOB

from .utc_datetime import UTCDateTime

__all__ = ("insert", "JSON", "BLOB", "UTCDateTime")

from typing import Union

from sqlalchemy import BLOB as StandardBLOB
from sqlalchemy import DateTime as StandardDateTime
from sqlalchemy import JSON as StandardJSON
from sqlalchemy.dialects.mysql import Insert as MysqlInsert
from sqlalchemy.dialects.postgresql import BYTEA as PostgresqlBYTEA
from sqlalchemy.dialects.postgresql import Insert as PostgresqlInsert
from sqlalchemy.dialects.sqlite import Insert as SqliteInsert
from sqlalchemy.sql import Insert as StandardInsert

insert = Union[StandardInsert, PostgresqlInsert, SqliteInsert, MysqlInsert]
JSON = StandardJSON
BLOB = Union[StandardBLOB, PostgresqlBYTEA]
UTCDateTime = StandardDateTime

__all__ = ("insert", "JSON", "BLOB", "UTCDateTime")

import json
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import AsyncContextManager

from nonebot import get_driver, logger
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, AsyncConnection
from sqlalchemy.orm import registry, sessionmaker
from sqlalchemy.pool import StaticPool

from ..lifecycle_mixin import DataSourceLifecycle
from ...errors import DataSourceNotReadyError
from ....config import Config
from ....global_context import context
from ....utils.lifecycler import on_startup, on_shutdown

conf = context.require(Config)


def default_dumps(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    return None


def json_serializer(obj):
    return json.dumps(obj, default=default_dumps)


@context.register_eager_singleton()
class DataSource(DataSourceLifecycle):
    app_db_version = 5
    registry = registry()

    def __init__(self):
        super().__init__()

        self._engine = None
        self._sessionmaker = None

        on_startup(replay=True)(self.initialize)
        on_shutdown()(self.close)

    async def _raw_get_db_version(self, conn: AsyncConnection) -> int:
        async with AsyncSession(conn, expire_on_commit=False) as session:
            from .meta_info import MetaInfo

            # 判断是否初次建库
            blank_database = not await conn.run_sync(lambda conn: inspect(conn).has_table("subscription"))
            if blank_database:
                result = MetaInfo(key="db_version", value=str(self.app_db_version))
                session.add(result)
                await session.commit()
                v = self.app_db_version
            else:
                stmt = select(MetaInfo).where(MetaInfo.key == "db_version")
                result = (await session.execute(stmt)).scalar_one_or_none()
                if result is None:
                    result = MetaInfo(key="db_version", value="1")
                    session.add(result)
                    await session.commit()

                v = int(result.value)
        return v

    async def _raw_set_db_version(self, db_version: int, conn: AsyncConnection):
        from .meta_info import MetaInfo
        async with AsyncSession(conn, expire_on_commit=False) as session:
            stmt = select(MetaInfo).where(MetaInfo.key == "db_version")
            result = (await session.execute(stmt)).scalar_one_or_none()
            if result is None:
                result = MetaInfo(key="db_version", value="1")
                session.add(result)

            result.value = str(db_version)
            await session.commit()

    async def initialize(self):
        await self._fire_initializing()

        driver = get_driver()

        params = {
            # 仅当TRACE模式时回显sql语句
            'echo': driver.config.log_level == 'TRACE',
            'future': True,
            'json_serializer': json_serializer
        }

        if conf.detect_sql_dialect == 'sqlite':
            # 使用 SQLite 数据库时，如果在写入时遇到 (sqlite3.OperationalError) database is locked 错误。
            # 可尝试将 poolclass 设置为 StaticPool，保持有且仅有一个连接。
            # 不过这样设置之后，在程序运行期间，你的数据库文件都将被占用。
            params['poolclass'] = StaticPool

        logger.info("[data source] sql conn url: " + conf.pixiv_sql_conn_url)
        self._engine = create_async_engine(conf.pixiv_sql_conn_url, **params)

        async with self._engine.begin() as conn:
            from .migration import SqlMigrationManager
            from .meta_info import MetaInfo

            await conn.run_sync(lambda conn: MetaInfo.__table__.create(conn, checkfirst=True))

            # migrate
            mig_mgr = SqlMigrationManager(lambda prev, cur: self._raw_set_db_version(cur, conn))
            db_version = await self._raw_get_db_version(conn)
            await mig_mgr.perform_migration(conn, db_version, self.app_db_version)

            await conn.run_sync(lambda conn: self.registry.metadata.create_all(conn))

            await conn.commit()

        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        self._sessionmaker = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)

        logger.success(f"[data source] SqlDataSource Initialized (dialect: {conf.pixiv_sql_dialect})")
        await self._fire_initialized()

    async def close(self):
        await self._fire_closing()

        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

        logger.success("[data source] SqlDataSource Disposed.")
        await self._fire_closed()

    @asynccontextmanager
    async def start_session(self) -> AsyncContextManager[AsyncSession]:
        if self._engine is None:
            raise DataSourceNotReadyError()
        async with self._sessionmaker() as session:
            yield session

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DataSourceNotReadyError()
        return self._engine


__all__ = ("DataSource",)

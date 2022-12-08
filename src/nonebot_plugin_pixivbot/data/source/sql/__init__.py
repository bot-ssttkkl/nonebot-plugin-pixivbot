import json
from contextlib import asynccontextmanager
from datetime import datetime, date

from nonebot import get_driver, logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, AsyncConnection
from sqlalchemy.orm import registry, sessionmaker

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.utils.lifecycler import on_startup, on_shutdown
from ..lifecycle_mixin import DataSourceLifecycleMixin
from ...errors import DataSourceNotReadyError


def default_dumps(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    return None


def json_serializer(obj):
    return json.dumps(obj, default=default_dumps)


@context.inject
class SqlDataSource(DataSourceLifecycleMixin):
    conf: Config = Inject(Config)
    app_db_version = 1

    def __init__(self):
        super().__init__()

        self._engine = None
        self._sessionmaker = None

        self._registry = registry()

        on_startup(replay=True)(self.initialize)
        on_shutdown()(self.close)

    @staticmethod
    async def _raw_get_db_version(conn: AsyncConnection) -> int:
        from .meta_info import MetaInfo
        async with AsyncSession(conn, expire_on_commit=False) as session:
            stmt = select(MetaInfo).where(MetaInfo.key == "db_version")
            result = (await session.execute(stmt)).scalar_one_or_none()
            if result is None:
                result = MetaInfo(key="db_version", value="1")
                session.add(result)
                await session.commit()

            return int(result.value)

    @staticmethod
    async def _raw_set_db_version(conn: AsyncConnection, db_version: int):
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
        self._engine = create_async_engine(self.conf.pixiv_sql_conn_url,
                                           # 仅当TRACE模式时回显sql语句
                                           echo=driver.config.log_level == 'TRACE',
                                           future=True,
                                           json_serializer=json_serializer)

        async with self._engine.begin() as conn:
            from .sql_migration import sql_migration_manager
            from .meta_info import MetaInfo

            await conn.run_sync(self._registry.metadata.create_all)

            # migrate
            db_version = await self._raw_get_db_version(conn)
            await sql_migration_manager.perform_migration(conn, db_version, self.app_db_version)
            await self._raw_set_db_version(conn, self.app_db_version)

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
    async def start_session(self):
        if self._engine is None:
            raise DataSourceNotReadyError()
        async with self._sessionmaker() as session:
            yield session

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DataSourceNotReadyError()
        return self._engine

    @property
    def registry(self) -> registry:
        return self._registry


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.sql:
    context.register_eager_singleton()(SqlDataSource)

__all__ = ("SqlDataSource",)

import json
from contextlib import asynccontextmanager
from datetime import datetime, date

from nonebot import get_driver, logger
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import registry, sessionmaker

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.global_context import context
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
    app_db_version = 4

    def __init__(self):
        super().__init__()

        self._engine = None
        self._sessionmaker = None

        self._registry = registry()

        on_startup(replay=True)(self.initialize)
        on_shutdown()(self.close)

    async def _raw_get_db_version(self) -> int:
        async with self._engine.begin() as conn:
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

            await conn.commit()
            return v

    async def _raw_set_db_version(self, db_version: int):
        from .meta_info import MetaInfo
        async with self._engine.begin() as conn:
            async with AsyncSession(conn, expire_on_commit=False) as session:
                stmt = select(MetaInfo).where(MetaInfo.key == "db_version")
                result = (await session.execute(stmt)).scalar_one_or_none()
                if result is None:
                    result = MetaInfo(key="db_version", value="1")
                    session.add(result)

                result.value = str(db_version)
                await session.commit()

            await conn.commit()

    async def initialize(self):
        await self._fire_initializing()

        driver = get_driver()
        self._engine = create_async_engine(self.conf.pixiv_sql_conn_url,
                                           # 仅当TRACE模式时回显sql语句
                                           echo=driver.config.log_level == 'TRACE',
                                           future=True,
                                           json_serializer=json_serializer)

        async with self._engine.begin() as conn:
            from .migration import SqlMigrationManager
            from .meta_info import MetaInfo

            await conn.run_sync(lambda conn: MetaInfo.__table__.create(conn, checkfirst=True))

            # migrate
            mig_mgr = SqlMigrationManager(lambda prev, cur: self._raw_set_db_version(cur))
            db_version = await self._raw_get_db_version()
            await mig_mgr.perform_migration(conn, db_version, self.app_db_version)

            await conn.run_sync(lambda conn: self._registry.metadata.create_all(conn))

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

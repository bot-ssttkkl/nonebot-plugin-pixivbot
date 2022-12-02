import json
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, date

from nonebot import get_driver, logger
from sqlalchemy.ext.asyncio import create_async_engine, async_scoped_session, AsyncSession, AsyncEngine
from sqlalchemy.orm import registry, sessionmaker

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.errors import DataSourceNotReadyError
from nonebot_plugin_pixivbot.data.source.lifecycle_mixin import DataSourceLifecycleMixin
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.utils.lifecycler import on_startup, on_shutdown


def default_dumps(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    return None


def json_serializer(obj):
    return json.dumps(obj, default=default_dumps)


@context.inject
class SqlDataSource(DataSourceLifecycleMixin):
    conf: Config = Inject(Config)

    def __init__(self):
        super().__init__()

        self._engine = None
        self._session = None

        self._registry = registry()

        self._session_scope = ContextVar("pixivbot_sql_session_scope")

        on_startup(self.initialize)
        on_shutdown(self.close)

    async def initialize(self):
        await self.fire_initializing()

        driver = get_driver()
        self._engine = create_async_engine(self.conf.pixiv_sql_conn_url,
                                           # 仅当TRACE模式时回显sql语句
                                           echo=driver.config.log_level == 'TRACE',
                                           future=True,
                                           json_serializer=json_serializer)

        async with self._engine.begin() as conn:
            await conn.run_sync(self._registry.metadata.create_all)

        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        session_factory = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        self._session = async_scoped_session(session_factory, scopefunc=self._session_scope.get)

        logger.success(f"[data source] SqlDataSource Initialized (dialect: {conf.pixiv_sql_dialect})")
        await self.fire_initialized()

    async def close(self):
        await self.fire_closing()

        await self._engine.dispose()

        self._engine = None
        self._session = None

        logger.success("[data source] SqlDataSource Disposed.")
        await self.fire_closed()

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DataSourceNotReadyError()
        return self._engine

    @property
    def registry(self) -> registry:
        return self._registry

    @property
    def session(self) -> async_scoped_session:
        if self._session is None:
            raise DataSourceNotReadyError()
        return self._session

    @asynccontextmanager
    async def session_scope(self):
        # 使用时间戳当作session标识
        session_id = time.time_ns()
        t_token = self._session_scope.set(session_id)
        try:
            logger.trace(f"new sql session scope {session_id}")
            yield
        finally:
            await self.session.remove()
            self._session_scope.reset(t_token)
            logger.trace(f"removed sql session scope {session_id}")


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.sql:
    context.register_eager_singleton()(SqlDataSource)

__all__ = ("SqlDataSource",)

import json
from datetime import datetime, date

from nonebot import get_driver, logger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import registry, sessionmaker

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.errors import DataSourceNotReadyError
from nonebot_plugin_pixivbot.data.source.lifecycle_mixin import DataSourceLifecycleMixin
from nonebot_plugin_pixivbot.data.source.session_scope_mixin import SessionScopeMixin
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.utils.lifecycler import on_startup, on_shutdown


def default_dumps(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    return None


def json_serializer(obj):
    return json.dumps(obj, default=default_dumps)


@context.inject
class SqlDataSource(DataSourceLifecycleMixin, SessionScopeMixin[AsyncSession]):
    conf: Config = Inject(Config)

    def __init__(self):
        super().__init__()

        self._engine = None
        self._sessionmaker = None

        self._registry = registry()

        on_startup(self.initialize)
        on_shutdown(self.close)

    async def initialize(self):
        await self._fire_initializing()

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

    async def _start_session(self) -> AsyncSession:
        if self._sessionmaker is None:
            raise DataSourceNotReadyError()
        return self._sessionmaker()

    async def _close_session(self, session: AsyncSession):
        await session.close()

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

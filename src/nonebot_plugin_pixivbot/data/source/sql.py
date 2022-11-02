import asyncio
import json
from datetime import datetime, date

from nonebot import get_driver, logger
from sqlalchemy.ext.asyncio import create_async_engine, async_scoped_session, AsyncSession, AsyncEngine
from sqlalchemy.orm import registry, sessionmaker

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.errors import DataSourceNotReadyError
from nonebot_plugin_pixivbot.enums import DataSourceType


def default_dumps(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    return None


def json_serializer(obj):
    return json.dumps(obj, default=default_dumps)


@context.inject
class SqlDataSource:
    conf: Config = Inject(Config)

    def __init__(self):
        self._engine = None
        self._session = None

        self._registry = registry()

        driver = get_driver()
        driver.on_startup(self.initialize)
        driver.on_shutdown(self.finalize)

    async def initialize(self):
        driver = get_driver()
        self._engine = create_async_engine(self.conf.pixiv_sql_conn_url,
                                           # 仅当debug模式时回显sql语句
                                           echo=driver.config.log_level.lower() == 'debug',
                                           future=True,
                                           json_serializer=json_serializer)

        async with self._engine.begin() as conn:
            await conn.run_sync(self._registry.metadata.create_all)

        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        session_factory = sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._session = async_scoped_session(
            session_factory, scopefunc=asyncio.current_task)
        logger.success("SqlDataSource Initialized.")

    async def finalize(self):
        await self._engine.dispose()

        self._engine = None
        self._session = None

        logger.success("SqlDataSource Disposed.")

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


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.sqlite:
    context.register_eager_singleton()(SqlDataSource)

__all__ = ("SqlDataSource",)

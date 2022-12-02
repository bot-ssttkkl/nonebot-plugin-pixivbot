from functools import wraps
from typing import Protocol, Callable, Union, Awaitable

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DataSourceType


class DataSource(Protocol):
    async def initialize(self):
        ...

    async def close(self):
        ...

    def on_initialized(self, func: Callable[[], Union[None, Awaitable[None]]]):
        ...

    def on_closed(self, func: Callable[[], Union[None, Awaitable[None]]]):
        ...


conf = context.require(Config)
if conf.pixiv_data_source == DataSourceType.mongo:
    from .mongo import MongoDataSource

    context.bind(DataSource, MongoDataSource)
else:
    from .sql import SqlDataSource

    context.bind(DataSource, SqlDataSource)


def with_session_scope_if_sql(action):
    @wraps(action)
    async def wrapper(*args, **kwargs):
        data_source = context.require(DataSource)
        if isinstance(data_source, SqlDataSource):
            async with data_source.session_scope():
                return await action(*args, **kwargs)
        else:
            return await action(*args, **kwargs)

    return wrapper


__all__ = ("DataSource",)

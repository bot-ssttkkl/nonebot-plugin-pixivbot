from typing import Callable

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.enums import DataSourceType
from nonebot_plugin_pixivbot.handler.interceptor.base import Interceptor, T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from ..pkg_context import context


@context.inject
@context.register_singleton()
class SqlSessionInterceptor(Interceptor):
    conf: Config = Inject(Config)
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool, **kwargs):
        if self.conf.pixiv_data_source == DataSourceType.sql:
            async with self.data_source.session_scope():
                await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        else:
            await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)

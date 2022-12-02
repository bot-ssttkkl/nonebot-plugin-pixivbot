from typing import Callable

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source import with_session_scope, DataSource
from nonebot_plugin_pixivbot.handler.interceptor.base import Interceptor, T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from ..pkg_context import context


@context.inject
@context.register_singleton()
class DataSourceSessionInterceptor(Interceptor):
    conf: Config = Inject(Config)
    data_source: DataSource = Inject(DataSource)

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool, **kwargs):
        await with_session_scope(wrapped_func)(*args, post_dest=post_dest, silently=silently, **kwargs)

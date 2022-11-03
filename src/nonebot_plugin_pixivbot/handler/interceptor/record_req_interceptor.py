from typing import Callable

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.handler.interceptor.base import Interceptor
from nonebot_plugin_pixivbot.handler.recorder import Recorder, Req
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from ..pkg_context import context


@context.inject
@context.register_singleton()
class RecordReqInterceptor(Interceptor):
    recorder = Inject(Recorder)

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[T_UID, T_GID],
                        silently: bool,
                        **kwargs):
        await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        self.recorder.record_req(Req(wrapped_func, *args, **kwargs), post_dest.identifier)

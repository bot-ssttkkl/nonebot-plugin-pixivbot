from typing import TypeVar, Callable

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common.recorder import Recorder, Req
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.inject
@context.register_singleton()
class RecordReqInterceptor(Interceptor):
    recorder: Recorder

    async def intercept(self, wrapped_func: Callable, *args,
                        post_dest: PostDestination[UID, GID],
                        silently: bool,
                        **kwargs):
        await wrapped_func(*args, post_dest=post_dest, silently=silently, **kwargs)
        self.recorder.record_req(Req(wrapped_func, *args, **kwargs), post_dest.identifier)

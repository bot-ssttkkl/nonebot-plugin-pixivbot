from typing import TypeVar, Callable

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.common.recorder import Recorder, Req
from nonebot_plugin_pixivbot.handler.interceptor.interceptor import Interceptor
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.register_singleton()
class RecordReqInterceptor(Interceptor):
    def __init__(self):
        self.recorder = context.require(Recorder)

    async def actual_intercept(self, wrapped_func: Callable, *,
                               post_dest: PostDestination[UID, GID],
                               silently: bool,
                               **kwargs):
        await wrapped_func(post_dest=post_dest, silently=silently, **kwargs)
        self.recorder.record_req(Req(wrapped_func, **kwargs), post_dest.identifier)

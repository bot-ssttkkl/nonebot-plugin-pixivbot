from typing import Callable, TYPE_CHECKING

from nonebot_plugin_pixivbot.handler.interceptor.base import Interceptor
from nonebot_plugin_pixivbot.handler.recorder import Recorder, Req
from ..pkg_context import context

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.handler.base import Handler

recorder = context.require(Recorder)


@context.register_singleton()
class RecordReqInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        await wrapped_func(*args, **kwargs)
        recorder.record_req(Req(type(handler), args, kwargs), handler.post_dest.identifier)

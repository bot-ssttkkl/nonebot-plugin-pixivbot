from typing import Callable, TYPE_CHECKING

from .base import Interceptor
from ..pkg_context import context
from ..recorder import Recorder, Req

if TYPE_CHECKING:
    from ..base import Handler

recorder = context.require(Recorder)


@context.register_singleton()
class RecordReqInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        await wrapped_func(*args, **kwargs)
        recorder.record_req(Req(type(handler), args, kwargs), handler.session)

from abc import ABC

from ..base import EntryHandler
from ..interceptor.loading_prompt_interceptor import LoadingPromptInterceptor
from ..interceptor.record_req_interceptor import RecordReqInterceptor
from ..interceptor.retry_interceptor import RetryInterceptor
from ..interceptor.timeout_interceptor import TimeoutInterceptor
from ..pkg_context import context


class CommonHandler(EntryHandler, ABC, interceptors=[
    context.require(TimeoutInterceptor),
    context.require(LoadingPromptInterceptor),
    context.require(RetryInterceptor)
]):
    pass


class RecordCommonHandler(CommonHandler, ABC, interceptors=[context.require(RecordReqInterceptor)]):
    pass

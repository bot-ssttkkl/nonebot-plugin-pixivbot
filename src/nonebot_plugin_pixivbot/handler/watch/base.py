from abc import ABC

from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from ..base import EntryHandler
from ..interceptor.retry_interceptor import RetryInterceptor
from ..interceptor.service_interceptor import ServiceInterceptor
from ..interceptor.timeout_interceptor import TimeoutInterceptor
from ..pkg_context import context
from ...plugin_service import receive_watch_service

service = context.require(PixivService)


class WatchTaskHandler(EntryHandler, ABC, interceptors=[
    ServiceInterceptor(receive_watch_service, acquire_rate_limit_token=False),
    context.require(TimeoutInterceptor),
    context.require(RetryInterceptor)
]):
    async def parse_args(self, args):
        raise RuntimeError("Please call handle_with_parsed_args() instead! ")

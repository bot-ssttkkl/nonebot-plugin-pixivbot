from abc import ABC

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from ..base import EntryHandler
from ..interceptor.retry_interceptor import RetryInterceptor
from ..interceptor.service_interceptor import ServiceInterceptor
from ..interceptor.timeout_interceptor import TimeoutInterceptor
from ..pkg_context import context
from ...plugin_service import receive_watch_service


@context.inject
class WatchTaskHandler(EntryHandler, ABC):
    service = Inject(PixivService)

    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(TimeoutInterceptor))
        self.add_interceptor(context.require(RetryInterceptor))
        self.add_interceptor(ServiceInterceptor(receive_watch_service, acquire_rate_limit_token=False))

    def parse_args(self, args, post_dest):
        raise RuntimeError("Please call handle_with_parsed_args() instead! ")

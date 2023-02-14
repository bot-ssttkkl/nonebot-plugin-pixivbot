from abc import ABC

from nonebot_plugin_pixivbot.handler.base import DelegationHandler
from nonebot_plugin_pixivbot.handler.interceptor.default_error_interceptor import DefaultErrorInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.record_req_interceptor import RecordReqInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.retry_interceptor import RetryInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.service_interceptor import ServiceInterceptor
from nonebot_plugin_pixivbot.handler.interceptor.timeout_interceptor import TimeoutInterceptor
from nonebot_plugin_pixivbot.handler.pkg_context import context
from nonebot_plugin_pixivbot.plugin_service import receive_schedule_service


class SubscriptionHandler(DelegationHandler, ABC):
    def __init__(self):
        super().__init__()
        self.interceptor = None

        self.add_interceptor(context.require(DefaultErrorInterceptor))
        self.add_interceptor(context.require(TimeoutInterceptor))
        self.add_interceptor(context.require(RetryInterceptor))
        self.add_interceptor(ServiceInterceptor(receive_schedule_service, acquire_rate_limit_token=False))
        self.add_interceptor(context.require(RecordReqInterceptor))

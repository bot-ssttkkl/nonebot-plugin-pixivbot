from abc import ABC

from nonebot_plugin_pixivbot.handler.base import EntryHandler
from nonebot_plugin_pixivbot.handler.interceptor.service_interceptor import ServiceInterceptor
from nonebot_plugin_pixivbot.plugin_service import receive_schedule_service


class SubscriptionHandler(EntryHandler, ABC, interceptors=[
    ServiceInterceptor(receive_schedule_service, acquire_rate_limit_token=False)
]):
    pass

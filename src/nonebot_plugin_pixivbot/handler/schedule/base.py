from abc import ABC

from nonebot_plugin_pixivbot.handler.base import EntryHandler
from nonebot_plugin_pixivbot.plugin_service import receive_schedule_service


class SubscriptionHandler(EntryHandler, ABC, service=receive_schedule_service,
                          service_interceptor_kwargs={"acquire_rate_limit_token": False}):
    pass

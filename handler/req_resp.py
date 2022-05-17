import time
import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

# from .abstract_handler import AbstractHandler


class Req:
    def __init__(self, handler: 'AbstractHandler', *args, **kwargs):
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()

    def __call__(self, *, bot: Bot,
                 event: MessageEvent = None,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None):
        return self.handler.handle(*self.args, bot=bot, event=event, user_id=user_id, group_id=group_id, **self.kwargs)


class Resp:
    def __init__(self, illust_id: int):
        self.illust_id = illust_id
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()

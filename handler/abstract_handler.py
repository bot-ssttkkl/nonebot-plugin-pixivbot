import time
import typing

from abc import ABC, abstractmethod
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..config import Config
from .pkg_context import context
from .recorder import Recorder
from .req_resp import Req


class AbstractHandler(ABC):
    conf = context.require(Config)
    recorder = context.require(Recorder)

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def enabled(cls) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> typing.Union[dict, typing.Awaitable[dict]]:
        raise NotImplementedError()

    @abstractmethod
    async def handle(self, *args, bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None,
                     **kwargs):
        raise NotImplementedError()

    def record_req(self, *args,
                   user_id: typing.Optional[int] = None,
                   group_id: typing.Optional[int] = None, **kwargs):
        self.recorder.record_req(Req(self, *args, **kwargs),
                                 user_id=user_id, group_id=group_id)

    def record_resp_illust(self, illust_id: int,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None, ):
        self.recorder.record_resp(
            illust_id, user_id=user_id, group_id=group_id)

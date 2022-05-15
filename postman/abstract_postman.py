import typing
from abc import ABC, abstractmethod

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..model import Illust


class AbstractPostman(ABC):
    @abstractmethod
    async def send_message(self, msg: typing.Union[str, Message],
                           *, event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        raise NotImplementedError()

    @abstractmethod
    async def send_illust(self, illust: Illust,
                          header: typing.Union[str,
                                               MessageSegment, None] = None,
                          number: typing.Optional[int] = None,
                          *, event: MessageEvent = None,
                          user_id: typing.Optional[int] = None,
                          group_id: typing.Optional[int] = None):
        raise NotImplementedError()

    @abstractmethod
    async def send_illusts(self, illusts: typing.Iterable[Illust],
                           header: typing.Union[str,
                                                MessageSegment, None] = None,
                           number: typing.Optional[int] = None,
                           *, event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        raise NotImplementedError()

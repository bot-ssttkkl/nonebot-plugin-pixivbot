import typing

from abc import ABC, abstractmethod
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent


class AbstractHandler(ABC):
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
    async def handle(self,
                     *, bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None,
                     **kwargs):
        raise NotImplementedError()


import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..errors import BadRequestError
from .pkg_context import context
from .abstract_handler import AbstractHandler
from .utils import fill_id


@context.export_singleton()
class MoreHandler(AbstractHandler):
    @classmethod
    def type(cls) -> str:
        return "more"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_more_enabled

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        return {}

    @fill_id
    async def handle(self, *, count: int = 1,
                     bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        req = self.recorder.get_req(user_id=user_id, group_id=group_id)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        await req(bot=bot, event=event, user_id=user_id, group_id=group_id)

import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..postman import Postman
from ..controller import Service
from ..config import Config
from ..errors import BadRequestError
from .pkg_context import context
from .abstract_handler import AbstractHandler


@context.export_singleton()
class IllustHandler(AbstractHandler):
    conf = context.require(Config)
    service = context.require(Service)
    postman = context.require(Postman)

    @classmethod
    def type(cls) -> str:
        return "illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_illust_query_enabled

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        try:
            return {"illust_id": int(command_args[0])}
        except ValueError:
            raise BadRequestError(f"{command_args[0]}不是合法的插画ID")

    async def handle(self, illust_id: int,
                     *, bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        illust = await self.service.illust_detail(illust_id)
        await self.postman.send_illust(illust,
                                       bot=bot, event=event, user_id=user_id, group_id=group_id)

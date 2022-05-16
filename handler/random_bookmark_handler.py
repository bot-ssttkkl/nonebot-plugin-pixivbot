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
class RandomBookmarkHandler(AbstractHandler):
    conf = context.require(Config)
    service = context.require(Service)
    postman = context.require(Postman)

    @classmethod
    def type(cls) -> str:
        return "random_bookmark"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_bookmark_query_enabled

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        d = {"sender_user_id": sender_user_id}

        if len(command_args) > 0:
            try:
                return {"pixiv_user_id": int(command_args[0])}
            except ValueError:
                raise BadRequestError(f"{command_args[0]}不是合法的ID")

        return d

    async def handle(self, sender_user_id: int,
                     pixiv_user_id: int = 0,
                     *, count: int = 1,
                     bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        illusts = await self.service.random_bookmark(sender_user_id, pixiv_user_id, count=count)
        await self.postman.send_illusts(illusts,
                                        header=f"这是您点的私家车",
                                        bot=bot, event=event, user_id=user_id, group_id=group_id)

import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..postman import Postman
from ..controller import Service
from ..config import Config
from .pkg_context import context
from .abstract_handler import AbstractHandler


@context.export_singleton()
class RandomIllustHandler(AbstractHandler):
    conf = context.require(Config)
    service = context.require(Service)
    postman = context.require(Postman)

    @classmethod
    def type(cls) -> str:
        return "random_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_illust_query_enabled

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        return {"word": command_args[0]}

    async def handle(self, word: str,
                     *, count: int = 1,
                     bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        illusts = await self.service.random_illust(word, count=count)
        await self.postman.send_illusts(illusts,
                                        header=f"这是您点的{word}图",
                                        bot=bot, event=event, user_id=user_id, group_id=group_id)

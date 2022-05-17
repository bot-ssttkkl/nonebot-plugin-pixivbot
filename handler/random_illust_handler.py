import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..postman import Postman
from ..controller import Service
from .pkg_context import context
from .abstract_handler import AbstractHandler
from .utils import fill_id


@context.export_singleton()
class RandomIllustHandler(AbstractHandler):
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

    @fill_id
    async def handle(self, word: str,
                     *, count: int = 1,
                     bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        illusts = await self.service.random_illust(word, count=count)

        # 记录请求
        self.record_req(word, count=count,
                        user_id=user_id, group_id=group_id)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id,
                                    user_id=user_id, group_id=group_id)

        await self.postman.send_illusts(illusts,
                                        header=f"这是您点的{word}图",
                                        bot=bot, event=event, user_id=user_id, group_id=group_id)

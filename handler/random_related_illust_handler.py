import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..postman import Postman
from ..service import PixivService
from ..errors import BadRequestError
from .pkg_context import context
from .abstract_handler import AbstractHandler
from .utils import fill_id


@context.root.register_singleton()
class RandomRelatedIllustHandler(AbstractHandler):
    service = context.require(PixivService)
    postman = context.require(Postman)

    @classmethod
    def type(cls) -> str:
        return "random_related_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_related_illust_query_enabled

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        return {}

    @fill_id
    async def handle(self, *, count: int = 1,
                     bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        illust_id = self.recorder.get_resp(user_id=user_id, group_id=group_id)
        if not illust_id:
            raise BadRequestError("你还没有发送过请求")

        illusts = await self.service.random_related_illust(illust_id, count=count)

        # 记录请求
        self.record_req(count=count,
                        user_id=user_id, group_id=group_id)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id,
                                    user_id=user_id, group_id=group_id)

        await self.postman.send_illusts(illusts,
                                        header=f"这是您点的[{illust_id}]的相关图片",
                                        bot=bot, event=event, user_id=user_id, group_id=group_id)

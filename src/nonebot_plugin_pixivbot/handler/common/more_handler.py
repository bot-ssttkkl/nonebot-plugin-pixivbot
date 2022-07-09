from typing import TypeVar, Generic

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.postman import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.root.register_singleton()
class MoreHandler(CommonHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    @classmethod
    def type(cls) -> str:
        return "more"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_more_enabled

    async def actual_handle(self, *, post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        req = self.recorder.get_req(post_dest.identifier)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        await req(post_dest=post_dest)

from typing import TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.postman import PostIdentifier, post_illust
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.root.register_singleton()
class IllustHandler(CommonHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    @classmethod
    def type(cls) -> str:
        return "illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_illust_query_enabled

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        try:
            return {"illust_id": int(args[0])}
        except ValueError:
            raise BadRequestError(f"{args[0]}不是合法的插画ID")

    async def actual_handle(self, *, illust_id: int,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        illust = await self.service.illust_detail(illust_id)
        await post_illust(illust, post_dest=post_dest)

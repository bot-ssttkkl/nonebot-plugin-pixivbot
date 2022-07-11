from typing import TypeVar, Generic, Sequence, Any

from nonebot import Bot
from nonebot.internal.adapter import Message

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.postman import PostDestination, PostIdentifier, post_illusts

UID = TypeVar("UID")
GID = TypeVar("GID")
B = TypeVar("B", bound=Bot)
M = TypeVar("M", bound=Message)


@context.root.register_singleton()
class RandomRecommendedIllustHandler(CommonHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    @classmethod
    def type(cls) -> str:
        return "random_recommended_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_recommended_illust_query_enabled

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {}

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        illusts = await self.service.random_recommended_illust(count=count)

        # 记录请求
        self.record_req(count=count, identifier=post_dest.identifier)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, identifier=post_dest.identifier)

        await post_illusts(illusts,
                           header="这是您点的图",
                           post_dest=post_dest)

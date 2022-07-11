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
class RandomIllustHandler(CommonHandler, Generic[UID, GID, B, M]):
    @classmethod
    def type(cls) -> str:
        return "random_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_illust_query_enabled

    def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        return {"word": args[0]}

    async def actual_handle(self, *, word: str,
                            count: int = 1,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        illusts = await self.service.random_illust(word, count=count)

        # 记录请求
        self.record_req(word, count=count, identifier=post_dest.identifier)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, identifier=post_dest.identifier)

        await post_illusts(illusts,
                           header=f"这是您点的{word}图",
                           post_dest=post_dest)

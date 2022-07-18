from typing import TypeVar, Sequence, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.utils import post_illusts
from nonebot_plugin_pixivbot.postman import PostDestination
from .common import CommonHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomIllustHandler(CommonHandler):
    @classmethod
    def type(cls) -> str:
        return "random_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_illust_query_enabled

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        return {"word": args[0]}

    async def actual_handle(self, *, word: str,
                            count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illusts = await self.service.random_illust(word, count=count)

        # 记录请求
        self.record_req(word, post_dest=post_dest, count=count)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, post_dest=post_dest)

        await post_illusts(illusts,
                           header=f"这是您点的{word}图",
                           post_dest=post_dest)

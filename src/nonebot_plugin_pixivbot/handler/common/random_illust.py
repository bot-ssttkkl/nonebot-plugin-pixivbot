from typing import TypeVar, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .common import CommonHandler
from ..interceptor.record_req_interceptor import RecordReqInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomIllustHandler(CommonHandler):
    def __init__(self):
        super().__init__()
        self.add_interceptor(context.require(RecordReqInterceptor))

    @classmethod
    def type(cls) -> str:
        return "random_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_illust_query_enabled

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[UID, GID]) -> dict:
        return {"word": args[0]}

    async def actual_handle(self, *, word: str,
                            count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illusts = await self.service.random_illust(word, count=count)

        await self.post_illusts(illusts,
                                header=f"这是您点的{word}图",
                                post_dest=post_dest)

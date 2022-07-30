from typing import TypeVar, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .common import CommonHandler
from .recorder import Recorder
from ..interceptor.record_req_interceptor import RecordReqInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomRelatedIllustHandler(CommonHandler):
    def __init__(self):
        super().__init__()
        self.recorder = context.require(Recorder)

        self.add_interceptor(context.require(RecordReqInterceptor))

    @classmethod
    def type(cls) -> str:
        return "random_related_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_related_illust_query_enabled

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[UID, GID]) -> dict:
        original_illust_id = self.recorder.get_resp(post_dest.identifier)
        if not original_illust_id:
            raise BadRequestError("你还没有发送过请求")
        return {"illust_id": original_illust_id}

    async def actual_handle(self, original_illust_id: int,
                            *, count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illusts = await self.service.random_related_illust(original_illust_id, count=count)

        await self.post_illusts(illusts,
                                header=f"这是您点的[{original_illust_id}]的相关图片",
                                post_dest=post_dest)

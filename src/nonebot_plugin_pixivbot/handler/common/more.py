from typing import TypeVar

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .common import CommonHandler
from .recorder import Recorder

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.inject
@context.root.register_singleton()
class MoreHandler(CommonHandler):
    recorder: Recorder

    @classmethod
    def type(cls) -> str:
        return "more"

    def enabled(self) -> bool:
        return self.conf.pixiv_more_enabled

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        req = self.recorder.get_req(post_dest.identifier)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        await req(count=count, post_dest=post_dest, silently=silently)

from typing import TypeVar, Sequence, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .common import CommonHandler
from ..interceptor.record_req_interceptor import RecordReqInterceptor

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomBookmarkHandler(CommonHandler):
    def __init__(self):
        super().__init__()
        self.binder = context.require(PixivAccountBinder)
        self.add_interceptor(context.require(RecordReqInterceptor))

    @classmethod
    def type(cls) -> str:
        return "random_bookmark"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_bookmark_query_enabled

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        pixiv_user_id = 0
        sender_user_id = post_dest.user_id

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": sender_user_id}

    async def actual_handle(self, *, sender_user_id: UID,
                            pixiv_user_id: int = 0,
                            count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await self.binder.get_binding(post_dest.adapter, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await self.service.random_bookmark(pixiv_user_id, count=count)

        await self.post_illusts(illusts,
                                header="这是您点的私家车",
                                post_dest=post_dest)

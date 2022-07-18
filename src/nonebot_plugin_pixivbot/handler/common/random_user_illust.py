from typing import TypeVar, Union, Sequence, Any

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.utils import post_illusts
from nonebot_plugin_pixivbot.postman import PostDestination
from .common import CommonHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomUserIllustHandler(CommonHandler):
    @classmethod
    def type(cls) -> str:
        return "random_user_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_user_illust_query_enabled

    async def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        user = args[0]
        if isinstance(user, str):
            user = await self.service.get_user(user)

        return {"user": user.id}

    async def actual_handle(self, *, user: Union[str, int],
                            count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        userinfo, illusts = await self.service.random_user_illust(user, count=count)

        # 记录请求
        self.record_req(userinfo.id, post_dest=post_dest, count=count)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, post_dest=post_dest)

        await post_illusts(illusts,
                           header=f"这是您点的{userinfo.name}老师({userinfo.id})的图",
                           post_dest=post_dest)

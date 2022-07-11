from typing import TypeVar, Generic

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.postman import PostDestination, post_illusts

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomRecommendedIllustHandler(CommonHandler[UID, GID], Generic[UID, GID]):
    @classmethod
    def type(cls) -> str:
        return "random_recommended_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_recommended_illust_query_enabled

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illusts = await self.service.random_recommended_illust(count=count)

        # 记录请求
        self.record_req(post_dest=post_dest, count=count)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, post_dest=post_dest)

        await post_illusts(illusts,
                           header="这是您点的图",
                           post_dest=post_dest)

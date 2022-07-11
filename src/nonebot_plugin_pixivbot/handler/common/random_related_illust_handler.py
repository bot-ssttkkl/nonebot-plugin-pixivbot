from typing import TypeVar, Generic

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.postman import PostDestination, post_illusts
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RandomRelatedIllustHandler(CommonHandler[UID, GID], Generic[UID, GID]):
    @classmethod
    def type(cls) -> str:
        return "random_related_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_related_illust_query_enabled

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illust_id = self.recorder.get_resp(PostIdentifier.from_post_dest(post_dest))
        if not illust_id:
            raise BadRequestError("你还没有发送过请求")

        illusts = await self.service.random_related_illust(illust_id, count=count)

        # 记录请求
        self.record_req(post_dest=post_dest, count=count)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, post_dest=post_dest)

        await post_illusts(illusts,
                           header=f"这是您点的[{illust_id}]的相关图片",
                           post_dest=post_dest)

from typing import TypeVar, Generic, Union, Sequence, Any

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
class RandomUserIllustHandler(CommonHandler[UID, GID, B, M], Generic[UID, GID, B, M]):
    @classmethod
    def type(cls) -> str:
        return "random_user_illust"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_random_user_illust_query_enabled

    async def parse_args(self, args: Sequence[Any], identifier: PostIdentifier[UID, GID]) -> dict:
        user = args[0]
        if isinstance(user, str):
            user = await self.service.get_user(user)

        return {"user": user.id}

    async def actual_handle(self, *, user: Union[str, int],
                            count: int = 1,
                            post_dest: PostDestination[UID, GID, B, M],
                            silently: bool = False):
        userinfo, illusts = await self.service.random_user_illust(user, count=count)

        # 记录请求
        self.record_req(userinfo.id, count=count, identifier=post_dest.identifier)
        # 记录结果
        if len(illusts) == 1:
            self.record_resp_illust(illusts[0].id, identifier=post_dest.identifier)

        await post_illusts(illusts,
                           header=f"这是您点的{userinfo.name}老师({userinfo.id})的图",
                           post_dest=post_dest)

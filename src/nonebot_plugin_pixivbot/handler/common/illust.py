from typing import TypeVar, Generic, Sequence

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .common import CommonHandler

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class IllustHandler(CommonHandler, Generic[UID, GID]):
    @classmethod
    def type(cls) -> str:
        return "illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_illust_query_enabled

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[UID, GID]) -> dict:
        try:
            return {"illust_id": int(args[0])}
        except ValueError:
            raise BadRequestError(f"{args[0]}不是合法的插画ID")

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, illust_id: int,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        illust = await self.service.illust_detail(illust_id)
        await self.post_illust(illust, post_dest=post_dest)

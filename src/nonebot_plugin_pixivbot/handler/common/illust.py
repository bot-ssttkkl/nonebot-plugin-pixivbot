from typing import Generic, Sequence

from nonebot import on_regex
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import illust_service
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import CommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...protocol_dep.post_dest import post_destination
from ...service.pixiv_service import PixivService

conf = context.require(Config)
service = context.require(PixivService)


class IllustHandler(CommonHandler, Generic[T_UID, T_GID], service=illust_service):
    @classmethod
    def type(cls) -> str:
        return "illust"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_illust_query_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        try:
            return {"illust_id": int(args[0])}
        except ValueError:
            raise BadRequestError(f"{args[0]}不是合法的插画ID")

    # noinspection PyMethodOverriding
    async def actual_handle(self, illust_id: int):
        illust = await service.illust_detail(illust_id)
        await self.post_illust(illust)


@on_regex(r"^看看图\s*([1-9][0-9]*)$", rule=get_common_query_rule(), priority=5).handle()
async def on_match(state: T_State,
                   post_dest=Depends(post_destination)):
    illust_id = state["_matched_groups"][0]
    await IllustHandler(post_dest).handle(illust_id)

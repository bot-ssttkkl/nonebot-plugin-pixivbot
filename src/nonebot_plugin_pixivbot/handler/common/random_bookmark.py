from typing import Sequence

from nonebot import on_regex
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.model import T_UID
from nonebot_plugin_pixivbot.plugin_service import random_bookmark_service
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule, get_count
from ...config import Config
from ...protocol_dep.post_dest import post_destination
from ...service.pixiv_service import PixivService

conf = context.require(Config)
binder = context.require(PixivAccountBinder)
service = context.require(PixivService)


class RandomBookmarkHandler(RecordCommonHandler, service=random_bookmark_service):
    @classmethod
    def type(cls) -> str:
        return "random_bookmark"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_random_bookmark_query_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        pixiv_user_id = 0
        sender_user_id = self.post_dest.user_id

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        # 因为群组的订阅会把PostIdentifier的user_id抹去，所以这里必须传递sender_user_id
        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": sender_user_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, sender_user_id: T_UID,
                            pixiv_user_id: int = 0,
                            count: int = 1):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(self.post_dest.adapter, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await service.random_bookmark(pixiv_user_id, count=count,
                                                exclude_r18=(not await self.is_r18_allowed()),
                                                exclude_r18g=(not await self.is_r18g_allowed()))

        await self.post_illusts(illusts,
                                header="这是您点的私家车")


@on_regex("^来(.*)?张私家车$", rule=get_common_query_rule(), priority=5).handle()
async def on_match(state: T_State,
                   post_dest=Depends(post_destination)):
    await RandomBookmarkHandler(post_dest).handle(count=get_count(state))

from typing import Sequence

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot_plugin_session import extract_session

from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule, ArgCount
from ...config import Config
from ...plugin_service import random_bookmark_service
from ...service.pixiv_account_binder import PixivAccountBinder
from ...service.pixiv_service import PixivService
from ...utils.errors import BadRequestError

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

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": self.session.id1}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, pixiv_user_id: int = 0,
                            sender_user_id: int = 0,
                            count: int = 1):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(self.session.platform, sender_user_id)

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
async def _(event: Event,
            session=Depends(extract_session),
            count=ArgCount()):
    await RandomBookmarkHandler(session, event).handle(count=count)

from typing import Sequence

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

from .base import CommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...plugin_service import illust_service
from ...service.pixiv_service import PixivService
from ...utils.errors import BadRequestError

conf = context.require(Config)
service = context.require(PixivService)


class IllustHandler(CommonHandler, service=illust_service):
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
async def _(event: Event,
            session=Depends(extract_session),
            matched_groups=RegexGroup()):
    illust_id = matched_groups[0]
    await IllustHandler(session, event).handle(illust_id)

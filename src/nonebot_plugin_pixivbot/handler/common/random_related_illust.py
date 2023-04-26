from typing import Sequence

from nonebot import on_regex
from nonebot.internal.params import Depends

from nonebot_plugin_pixivbot.plugin_service import random_related_illust_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import post_destination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import RecordCommonHandler
from ..pkg_context import context
from ..recorder import Recorder
from ..utils import get_common_query_rule
from ...config import Config
from ...service.pixiv_service import PixivService

conf = context.require(Config)
service = context.require(PixivService)
recorder = context.require(Recorder)


class RandomRelatedIllustHandler(RecordCommonHandler, service=random_related_illust_service):
    @classmethod
    def type(cls) -> str:
        return "random_related_illust"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_random_related_illust_query_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        illust_id = recorder.get_resp(self.post_dest.identifier)
        if not illust_id:
            raise BadRequestError("你还没有发送过请求")
        return {"illust_id": illust_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, illust_id: int,
                            count: int = 1):
        illusts = await service.random_related_illust(illust_id, count=count,
                                                      exclude_r18=(not await self.is_r18_allowed()),
                                                      exclude_r18g=(not await self.is_r18g_allowed()))

        await self.post_illusts(illusts,
                                header=f"这是您点的[{illust_id}]的相关图片")


@on_regex("^不够色$", rule=get_common_query_rule(), priority=1, block=True).handle()
async def on_match(post_dest=Depends(post_destination)):
    await RandomRelatedIllustHandler(post_dest).handle()

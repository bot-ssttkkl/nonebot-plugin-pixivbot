from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot_plugin_session import extract_session

from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule, ArgCount
from ...config import Config
from ...plugin_service import random_recommended_illust_service
from ...service.pixiv_service import PixivService

conf = context.require(Config)
service = context.require(PixivService)


class RandomRecommendedIllustHandler(RecordCommonHandler, service=random_recommended_illust_service):
    @classmethod
    def type(cls) -> str:
        return "random_recommended_illust"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_random_recommended_illust_query_enabled

    async def actual_handle(self, *, count: int = 1):
        illusts = await service.random_recommended_illust(count=count,
                                                          exclude_r18=(not await self.is_r18_allowed()),
                                                          exclude_r18g=(not await self.is_r18g_allowed()))

        await self.post_illusts(illusts,
                                header="这是您点的图")


@on_regex("^来(.*)?张图$", rule=get_common_query_rule(), priority=3, block=True).handle()
async def _(event: Event,
            session=Depends(extract_session),
            count=ArgCount()):
    await RandomRecommendedIllustHandler(session, event).handle(count=count)

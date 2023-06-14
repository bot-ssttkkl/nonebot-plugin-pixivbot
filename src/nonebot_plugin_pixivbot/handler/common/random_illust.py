from typing import Sequence

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule, ArgCount
from ...config import Config
from ...plugin_service import random_illust_service
from ...service.pixiv_service import PixivService

conf = context.require(Config)
service = context.require(PixivService)


class RandomIllustHandler(RecordCommonHandler, service=random_illust_service):
    @classmethod
    def type(cls) -> str:
        return "random_illust"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_random_illust_query_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        return {"word": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, word: str,
                            count: int = 1):
        illusts = await service.random_illust(word, count=count,
                                              exclude_r18=(not await self.is_r18_allowed()),
                                              exclude_r18g=(not await self.is_r18g_allowed()))

        await self.post_illusts(illusts,
                                header=f"这是您点的{word}图")


@on_regex("^来(.*)?张(.+)图$", rule=get_common_query_rule(), priority=5).handle()
async def _(event: Event,
            matched_groups=RegexGroup(),
            session=Depends(extract_session),
            count=ArgCount()):
    word = matched_groups[1]
    await RandomIllustHandler(session, event).handle(word, count=count)

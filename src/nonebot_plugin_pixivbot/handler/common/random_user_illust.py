from typing import Sequence
from typing import Union

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

from nonebot_plugin_pixivbot.plugin_service import random_user_illust_service
from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule, ArgCount
from ...config import Config
from ...service.pixiv_service import PixivService

conf = context.require(Config)
service = context.require(PixivService)


class RandomUserIllustHandler(RecordCommonHandler, service=random_user_illust_service):
    @classmethod
    def type(cls) -> str:
        return "random_user_illust"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_random_user_illust_query_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        try:
            user_id = int(args[0])
            return {"user": user_id}
        except ValueError:
            user = await service.get_user(args[0])
            return {"user": user.id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, user: Union[str, int],
                            count: int = 1):
        userinfo, illusts = await service.random_user_illust(user, count=count,
                                                             exclude_r18=(not await self.is_r18_allowed()),
                                                             exclude_r18g=(not await self.is_r18g_allowed()))

        await self.post_illusts(illusts,
                                header=f"这是您点的{userinfo.name}({userinfo.id})老师的图")


@on_regex("^来(.*)?张(.+)老师的图$", rule=get_common_query_rule(), priority=4, block=True).handle()
async def _(event: Event,
            matched_groups=RegexGroup(),
            session=Depends(extract_session),
            count=ArgCount()):
    user = matched_groups[1]
    await RandomUserIllustHandler(session, event).handle(user, count=count)

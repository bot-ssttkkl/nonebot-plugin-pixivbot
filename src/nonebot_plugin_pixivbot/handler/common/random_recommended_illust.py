from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import RecordCommonHandler
from ..base import post_destination
from ..pkg_context import context
from ..utils import get_common_query_rule, get_count


@context.root.register_eager_singleton()
class RandomRecommendedIllustHandler(RecordCommonHandler):
    @classmethod
    def type(cls) -> str:
        return "random_recommended_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_recommended_illust_query_enabled

    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张图$", rule=get_common_query_rule(), priority=3, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        await self.handle(count=get_count(state), post_dest=post_dest)

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        illusts = await self.service.random_recommended_illust(count=count)

        await self.post_illusts(illusts,
                                header="这是您点的图",
                                post_dest=post_dest)

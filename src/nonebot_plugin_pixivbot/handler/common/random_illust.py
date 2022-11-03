from typing import Sequence

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
class RandomIllustHandler(RecordCommonHandler):
    @classmethod
    def type(cls) -> str:
        return "random_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_illust_query_enabled

    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张(.+)图$", rule=get_common_query_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        word = state["_matched_groups"][1]
        await self.handle(word, count=get_count(state), post_dest=post_dest)

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        return {"word": args[0]}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, word: str,
                            count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        illusts = await self.service.random_illust(word, count=count)

        await self.post_illusts(illusts,
                                header=f"这是您点的{word}图",
                                post_dest=post_dest)

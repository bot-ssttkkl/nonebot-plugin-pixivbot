from typing import Generic, Sequence

from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import CommonHandler
from ..base import post_destination
from ..pkg_context import context
from ..utils import get_common_query_rule


@context.root.register_eager_singleton()
class IllustHandler(CommonHandler, Generic[T_UID, T_GID]):
    @classmethod
    def type(cls) -> str:
        return "illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_illust_query_enabled

    @lazy
    def matcher(self):
        return on_regex(r"^看看图\s*([1-9][0-9]*)$", rule=get_common_query_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        illust_id = state["_matched_groups"][0]
        await self.handle(illust_id, post_dest=post_dest)

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        try:
            return {"illust_id": int(args[0])}
        except ValueError:
            raise BadRequestError(f"{args[0]}不是合法的插画ID")

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, illust_id: int,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False, **kwargs):
        illust = await self.service.illust_detail(illust_id)
        await self.post_illust(illust, post_dest=post_dest)

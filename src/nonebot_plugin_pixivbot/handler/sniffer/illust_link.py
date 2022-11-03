from typing import Type

from nonebot import Bot, on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from ..base import DelegationHandler, T_UID, T_GID, MatcherEntryHandler, post_destination
from ..common import IllustHandler
from ..pkg_context import context
from ..utils import get_common_query_rule


@context.root.register_eager_singleton()
class IllustLinkHandler(DelegationHandler, MatcherEntryHandler):
    @classmethod
    def type(cls) -> str:
        return "illust_link"

    def enabled(self) -> bool:
        return True

    @property
    def delegation(self) -> DelegationHandler:
        return context.require(IllustHandler)

    @property
    def matcher(self) -> Type[Matcher]:
        return on_regex(r"^(http://|https://)?(www.)?pixiv\.net/artworks/([1-9][0-9]*)/?$",
                        rule=get_common_query_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        illust_id = state["_matched_groups"][2]
        await self.handle(illust_id, post_dest=post_dest)

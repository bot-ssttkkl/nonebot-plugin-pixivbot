from typing import Sequence

from lazy import lazy
from nonebot import on_regex
from nonebot.adapters import Bot, Event
from nonebot.internal.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import CommonHandler
from ..base import post_destination
from ..pkg_context import context
from ..recorder import Recorder
from ..utils import get_common_query_rule
from ...utils.decode_integer import decode_integer


@context.inject
@context.root.register_eager_singleton()
class MoreHandler(CommonHandler):
    recorder = Inject(Recorder)

    @classmethod
    def type(cls) -> str:
        return "more"

    def enabled(self) -> bool:
        return self.conf.pixiv_more_enabled

    @lazy
    def matcher(self):
        return on_regex("^还要((.*)张)?$", rule=get_common_query_rule(), priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        count = state["_matched_groups"][1]
        await self.handle(count, post_dest=post_dest)

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        count = decode_integer(args[0]) if args[0] is not None else 1
        return dict(count=count)

    async def actual_handle(self, *, count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False,
                            **kwargs):
        req = self.recorder.get_req(post_dest.identifier)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        await req(count=count, post_dest=post_dest, silently=silently)

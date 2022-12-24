from typing import Sequence
from typing import Union

from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import random_user_illust_service, r18_service, r18g_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .base import RecordCommonHandler
from ..base import post_destination
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context
from ..utils import get_common_query_rule, get_count


@context.root.register_eager_singleton()
class RandomUserIllustHandler(RecordCommonHandler):
    def __init__(self):
        super().__init__()
        self.add_interceptor(ServiceInterceptor(random_user_illust_service))

    @classmethod
    def type(cls) -> str:
        return "random_user_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_user_illust_query_enabled

    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张(.+)老师的图$", rule=get_common_query_rule(), priority=4, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        user = state["_matched_groups"][1]
        await self.handle(user, count=get_count(state), post_dest=post_dest)

    async def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        try:
            user_id = int(args[0])
            return {"user": user_id}
        except ValueError:
            user = await self.service.get_user(args[0])
            return {"user": user.id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, user: Union[str, int],
                            count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        exclude_r18 = not await r18_service.get_permission(*post_dest.extract_subjects())
        exclude_r18g = not await r18g_service.get_permission(*post_dest.extract_subjects())

        userinfo, illusts = await self.service.random_user_illust(user, count=count,
                                                                  exclude_r18=exclude_r18,
                                                                  exclude_r18g=exclude_r18g)

        await self.post_illusts(illusts,
                                header=f"这是您点的{userinfo.name}({userinfo.id})老师的图",
                                post_dest=post_dest)

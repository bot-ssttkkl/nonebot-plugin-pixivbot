from typing import Sequence

from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import RecordCommonHandler
from ..base import post_destination
from ..pkg_context import context
from ..utils import get_common_query_rule, get_count, get_post_dest


@context.inject
@context.root.register_eager_singleton()
class RandomBookmarkHandler(RecordCommonHandler):
    binder = Inject(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "random_bookmark"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_bookmark_query_enabled

    @lazy
    def matcher(self):
        return on_regex("^来(.*)?张私家车$", rule=get_common_query_rule(), priority=5)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        await self.handle(count=get_count(state), post_dest=get_post_dest(bot, event))

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        pixiv_user_id = 0
        sender_user_id = post_dest.user_id

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        # 因为群组的订阅会把PostIdentifier的user_id抹去，所以这里必须传递sender_user_id
        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": sender_user_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, sender_user_id: T_UID,
                            pixiv_user_id: int = 0,
                            count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await self.binder.get_binding(post_dest.adapter, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await self.service.random_bookmark(pixiv_user_id, count=count)

        await self.post_illusts(illusts,
                                header="这是您点的私家车",
                                post_dest=post_dest)

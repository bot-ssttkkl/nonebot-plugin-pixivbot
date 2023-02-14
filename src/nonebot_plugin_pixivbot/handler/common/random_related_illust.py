from typing import Sequence

from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.plugin_service import random_related_illust_service, r18_service, r18g_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import RecordCommonHandler
from ..base import post_destination
from ..interceptor.record_req_interceptor import RecordReqInterceptor
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context
from ..recorder import Recorder
from ..utils import get_common_query_rule


@context.inject
@context.root.register_eager_singleton()
class RandomRelatedIllustHandler(RecordCommonHandler):
    recorder = Inject(Recorder)

    def __init__(self):
        super().__init__()
        self.add_interceptor(ServiceInterceptor(random_related_illust_service), before=RecordReqInterceptor)

    @classmethod
    def type(cls) -> str:
        return "random_related_illust"

    def enabled(self) -> bool:
        return self.conf.pixiv_random_related_illust_query_enabled

    @lazy
    def matcher(self):
        return on_regex("^不够色$", rule=get_common_query_rule(), priority=1, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        await self.handle(post_dest=post_dest)

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        illust_id = self.recorder.get_resp(post_dest.identifier)
        if not illust_id:
            raise BadRequestError("你还没有发送过请求")
        return {"illust_id": illust_id}

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, illust_id: int,
                            count: int = 1,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        exclude_r18 = not await r18_service.check_by_subject(*post_dest.extract_subjects(),
                                                             acquire_rate_limit_token=False)
        exclude_r18g = not await r18g_service.check_by_subject(*post_dest.extract_subjects(),
                                                               acquire_rate_limit_token=False)

        illusts = await self.service.random_related_illust(illust_id, count=count,
                                                           exclude_r18=exclude_r18,
                                                           exclude_r18g=exclude_r18g)

        await self.post_illusts(illusts,
                                header=f"这是您点的[{illust_id}]的相关图片",
                                post_dest=post_dest)

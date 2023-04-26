from nonebot import on_regex
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.plugin_service import more_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import post_destination
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import CommonHandler
from ..pkg_context import context
from ..recorder import Recorder
from ..utils import get_common_query_rule, get_count
from ...config import Config

recorder = context.require(Recorder)
conf = context.require(Config)


class MoreHandler(CommonHandler, service=more_service):
    @classmethod
    def type(cls) -> str:
        return "more"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_more_enabled

    async def actual_handle(self, count: int = 1):
        req = recorder.get_req(self.post_dest.identifier)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        handler = req.handler_type(self.post_dest, silently=self.silently, disable_interceptors=True)
        await handler.handle(*req.args, **{**req.kwargs, "count": count})


@on_regex("^还要((.*)张)?$", rule=get_common_query_rule(), priority=1, block=True).handle()
async def on_match(state: T_State,
                   post_dest=Depends(post_destination)):
    await MoreHandler(post_dest).handle(count=get_count(state, 1))

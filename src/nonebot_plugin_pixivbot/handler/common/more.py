from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot_plugin_session import extract_session

from .base import CommonHandler
from ..pkg_context import context
from ..recorder import Recorder
from ..utils import get_common_query_rule, ArgCount
from ...config import Config
from ...plugin_service import more_service
from ...utils.errors import BadRequestError

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
        req = recorder.get_req(self.session)
        if not req:
            raise BadRequestError("你还没有发送过请求")

        handler = req.handler_type(self.session, silently=self.silently, disable_interceptors=True)
        await handler.handle(*req.args, **{**req.kwargs, "count": count})


@on_regex("^还要((.*)张)?$", rule=get_common_query_rule(), priority=1, block=True).handle()
async def _(event: Event,
            session=Depends(extract_session),
            count=ArgCount(1)):
    await MoreHandler(session, event).handle(count=count)

from nonebot import on_regex
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.protocol_dep.post_dest import post_destination
from ..common import IllustHandler
from ..interceptor.default_error_interceptor import DefaultErrorInterceptor
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...plugin_service import illust_link_service

conf = context.require(Config)


class IllustLinkHandler(IllustHandler):
    @classmethod
    def type(cls) -> str:
        return "illust_link"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_illust_sniffer_enabled


IllustLinkHandler.add_interceptor_after(ServiceInterceptor(illust_link_service),
                                        after=context.require(DefaultErrorInterceptor))


@on_regex(r"^(http://|https://)?(www.)?pixiv\.net/artworks/([1-9][0-9]*)/?$", rule=get_common_query_rule(),
          priority=5).handle()
async def on_match(state: T_State,
                   post_dest=Depends(post_destination)):
    illust_id = state["_matched_groups"][2]
    await IllustLinkHandler(post_dest).handle(illust_id)

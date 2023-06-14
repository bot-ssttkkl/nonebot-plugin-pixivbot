from nonebot import on_regex
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup

from nonebot_plugin_pixivbot.protocol_dep.post_dest import post_destination
from ..common import IllustHandler
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...plugin_service import illust_link_service

conf = context.require(Config)


class IllustLinkHandler(IllustHandler, service=illust_link_service):
    @classmethod
    def type(cls) -> str:
        return "illust_link"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_illust_sniffer_enabled


@on_regex(r"^(http://|https://)?(www.)?pixiv\.net/artworks/([1-9][0-9]*)/?$", rule=get_common_query_rule(),
          priority=5).handle()
async def on_match(matched_groups=RegexGroup(),
                   post_dest=Depends(post_destination)):
    illust_id = matched_groups[2]
    await IllustLinkHandler(post_dest).handle(illust_id)

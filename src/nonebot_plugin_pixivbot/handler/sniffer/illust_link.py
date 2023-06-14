from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

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
async def _(event: Event,
            matched_groups=RegexGroup(),
            session=Depends(extract_session)):
    illust_id = matched_groups[2]
    await IllustLinkHandler(session, event).handle(illust_id)

from abc import ABC

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
from ..base import EntryHandler
from ..pkg_context import context


@context.inject
class WatchTaskHandler(EntryHandler, ABC):
    service = Inject(PixivService)

    def parse_args(self, args, post_dest):
        raise RuntimeError("Please call handle_with_parsed_args() instead! ")

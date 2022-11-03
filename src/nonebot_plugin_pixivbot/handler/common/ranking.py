from typing import Sequence
from typing import Tuple
from typing import Union

from lazy import lazy
from nonebot import on_regex, Bot
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from nonebot_plugin_pixivbot.enums import RankingMode
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.decode_integer import decode_integer
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from .base import CommonHandler
from ..base import post_destination
from ..pkg_context import context
from ..utils import get_common_query_rule


@context.root.register_eager_singleton()
class RankingHandler(CommonHandler):
    @classmethod
    def type(cls) -> str:
        return "ranking"

    mode_mapping = {RankingMode.day: "日", RankingMode.week: "周", RankingMode.month: "月",
                    RankingMode.day_male: "男性", RankingMode.day_female: "女性", RankingMode.week_original: "原创",
                    RankingMode.week_rookie: "新人", RankingMode.day_manga: "漫画"}

    mode_rev_mapping = {}
    for mode, text in mode_mapping.items():
        mode_rev_mapping[text] = mode

    def enabled(self) -> bool:
        return self.conf.pixiv_ranking_query_enabled

    @lazy
    def matcher(self):
        return on_regex(r"^看看(.*)?榜\s*(.*)?$", rule=get_common_query_rule(), priority=4, block=True)

    async def on_match(self, bot: Bot, event: Event, state: T_State, matcher: Matcher,
                       post_dest: PostDestination[T_UID, T_GID] = Depends(post_destination)):
        if "_matched_groups" in state:
            mode = state["_matched_groups"][0]
            num = state["_matched_groups"][1]
        else:
            mode = None
            num = None
        await self.handle(mode, num, post_dest=post_dest)

    def validate_range(self, range: Tuple[int, int] = None):
        if range:
            start, end = range
            if end - start + 1 > self.conf.pixiv_ranking_max_item_per_query:
                raise BadRequestError(
                    f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_query}张以下插画")
            elif start > end:
                raise BadRequestError("范围不合法")
            elif end > self.conf.pixiv_ranking_fetch_item:
                raise BadRequestError(
                    f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')

    def parse_args(self, args: Sequence[str], post_dest: PostDestination[T_UID, T_GID]) -> dict:
        mode = args[0] if len(args) > 0 else None
        range = args[1] if len(args) > 1 else None

        if not mode:  # 判断是不是空字符串
            mode = None
        elif mode in self.mode_rev_mapping:
            mode = self.mode_rev_mapping[mode]
        elif isinstance(mode, str):
            try:
                mode = RankingMode[mode]
            except:
                raise BadRequestError(f"{mode}不是合法的榜单类型")

        if not range:
            range = None
        else:
            try:
                if "-" in range:
                    start, end = range.split("-")
                    range = int(start), int(end)
                else:
                    range = decode_integer(range)
                    range = range, range
            except ValueError:
                raise BadRequestError(f"{range}不是合法的范围")

        return {"mode": mode, "range": range}

    async def actual_handle(self, *, mode: Union[RankingMode, None] = None,
                            range: Union[Tuple[int, int], int, None] = None,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False):
        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        if isinstance(range, int):
            range = range, range

        self.validate_range(range)
        illusts = await self.service.illust_ranking(mode, range)
        await self.post_illusts(illusts,
                                header=f"这是您点的{self.mode_mapping[mode]}榜",
                                number=range[0],
                                post_dest=post_dest)

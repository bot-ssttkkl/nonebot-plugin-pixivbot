from typing import Sequence
from typing import Tuple
from typing import Union

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

from .base import CommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...enums import RankingMode
from ...plugin_service import ranking_service
from ...service.pixiv_service import PixivService
from ...utils.decode_integer import decode_integer
from ...utils.errors import BadRequestError

conf = context.require(Config)
service = context.require(PixivService)


class RankingHandler(CommonHandler, service=ranking_service):
    @classmethod
    def type(cls) -> str:
        return "ranking"

    mode_mapping = {RankingMode.day: "日", RankingMode.week: "周", RankingMode.month: "月",
                    RankingMode.day_male: "男性", RankingMode.day_female: "女性", RankingMode.week_original: "原创",
                    RankingMode.week_rookie: "新人", RankingMode.day_manga: "漫画", RankingMode.day_ai: 'ai'}

    mode_rev_mapping = {}
    for mode, text in mode_mapping.items():
        mode_rev_mapping[text] = mode

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_ranking_query_enabled

    def validate_range(self, range: Tuple[int, int] = None):
        if range:
            start, end = range
            if end - start + 1 > conf.pixiv_ranking_max_item_per_query:
                raise BadRequestError(
                    f"仅支持一次查询{conf.pixiv_ranking_max_item_per_query}张以下插画")
            elif start > end:
                raise BadRequestError("范围不合法")
            elif end > conf.pixiv_ranking_fetch_item:
                raise BadRequestError(
                    f'仅支持查询{conf.pixiv_ranking_fetch_item}名以内的插画')

    async def parse_args(self, args: Sequence[str]) -> dict:
        mode = args[0].lower() if len(args) > 0 else None
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
                            range: Union[Tuple[int, int], int, None] = None):
        if mode is None:
            mode = conf.pixiv_ranking_default_mode

        if range is None:
            range = conf.pixiv_ranking_default_range

        if isinstance(range, int):
            range = range, range

        self.validate_range(range)
        illusts = await service.illust_ranking(mode, range)
        await self.post_illusts(illusts,
                                header=f"这是您点的{self.mode_mapping[mode]}榜",
                                number=range[0])


@on_regex(r"^看看(.*)?榜\s*(.*)?$", rule=get_common_query_rule(), priority=4, block=True).handle()
async def on_match(event: Event,
                   matched_groups=RegexGroup(),
                   session=Depends(extract_session)):
    if matched_groups:
        mode = matched_groups[0]
        num = matched_groups[1]
    else:
        mode = None
        num = None
    await RankingHandler(session, event).handle(mode, num)

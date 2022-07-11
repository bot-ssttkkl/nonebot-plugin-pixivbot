from typing import Optional, Sequence, Union, TypeVar, Generic, Any

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.handler.common.common_handler import CommonHandler
from nonebot_plugin_pixivbot.postman import PostDestination, post_illusts
from nonebot_plugin_pixivbot.utils.decode_integer import decode_integer
from nonebot_plugin_pixivbot.utils.errors import BadRequestError

UID = TypeVar("UID")
GID = TypeVar("GID")


@context.root.register_singleton()
class RankingHandler(CommonHandler[UID, GID], Generic[UID, GID]):
    @classmethod
    def type(cls) -> str:
        return "ranking"

    mode_mapping = {"日": "day", "周": "week", "月": "month", "男性": "day_male",
                    "女性": "day_female", "原创": "week_original", "新人": "week_rookie", "漫画": "day_manga"}

    mode_reversed_mapping = {"day": "日", "week": "周", "month": "月", "day_male": "男性",
                             "day_female": "女性", "week_original": "原创", "week_rookie": "新人", "day_manga": "漫画"}

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_ranking_query_enabled

    def validate_args(self, mode: Optional[str] = None,
                      range: Optional[Sequence[int]] = None):
        if mode and mode not in self.mode_reversed_mapping:
            raise BadRequestError(f"{mode}不是合法的榜单类型")

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

    def parse_args(self, args: Sequence[Any], post_dest: PostDestination[UID, GID]) -> dict:
        mode = args[0] if len(args) > 0 else None
        range = args[1] if len(args) > 1 else None

        if not mode:  # 判断是不是空字符串
            mode = None
        elif mode in self.mode_mapping:
            mode = self.mode_mapping[mode]

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

        self.validate_args(mode, range)
        return {"mode": mode, "range": range}

    async def actual_handle(self, *, mode: Optional[str] = None,
                            range: Union[Sequence[int], int, None] = None,
                            post_dest: PostDestination[UID, GID],
                            silently: bool = False):
        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        if isinstance(range, int):
            range = range, range

        self.validate_args(mode, range)
        illusts = await self.service.illust_ranking(mode, range)
        await post_illusts(illusts,
                           header=f"这是您点的{self.mode_reversed_mapping[mode]}榜",
                           number=range[0],
                           post_dest=post_dest)

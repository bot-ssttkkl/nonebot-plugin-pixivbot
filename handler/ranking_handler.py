import typing

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..postman import Postman
from ..utils import decode_integer
from ..controller import Service
from ..errors import BadRequestError
from ..config import Config
from .pkg_context import context
from .abstract_handler import AbstractHandler


@context.export_singleton()
class RankingHandler(AbstractHandler):
    conf = context.require(Config)
    service = context.require(Service)
    postman = context.require(Postman)

    mode_mapping = {"日": "day", "周": "week", "月": "month", "男性": "day_male",
                    "女性": "day_female", "原创": "week_original", "新人": "week_rookie", "漫画": "day_manga"}

    mode_reversed_mapping = {"day": "日", "week": "周", "month": "月", "day_male": "男性",
                             "day_female": "女性", "week_original": "原创", "week_rookie": "新人", "day_manga": "漫画"}

    @classmethod
    def type(cls) -> str:
        return "ranking"

    @classmethod
    def enabled(cls) -> bool:
        return cls.conf.pixiv_ranking_query_enabled

    def validate_args(self, mode: typing.Optional[str] = None,
                      range: typing.Union[typing.Sequence[int], int, None] = None):
        if mode and mode not in self.mode_reversed_mapping:
            raise BadRequestError(f"{mode}不是合法的榜单类型")

        if range:
            if isinstance(range, int):
                num = range
                if num > self.conf.pixiv_ranking_fetch_item:
                    raise BadRequestError(
                        f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                start, end = range
                if end - start + 1 > self.conf.pixiv_ranking_max_item_per_query:
                    raise BadRequestError(
                        f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_query}张以下插画")
                elif start > end:
                    raise BadRequestError("范围不合法")
                elif end > self.conf.pixiv_ranking_fetch_item:
                    raise BadRequestError(
                        f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')

    def parse_command_args(self, command_args: list[str], sender_user_id: int = 0) -> dict:
        mode = command_args[0] if len(command_args) > 0 else None
        range = command_args[1] if len(command_args) > 1 else None

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
            except ValueError:
                raise BadRequestError(f"{range}不是合法的范围")

        self.validate_args(mode, range)
        return {"mode": mode, "range": range}

    async def handle(self, mode: typing.Optional[str] = None,
                     range: typing.Union[typing.Sequence[int],
                                         int, None] = None,
                     *, bot: Bot,
                     event: MessageEvent = None,
                     user_id: typing.Optional[int] = None,
                     group_id: typing.Optional[int] = None):
        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        self.validate_args(mode, range)
        illusts = await self.service.illust_ranking(mode, range)
        await self.postman.send_illusts(illusts,
                                        header=f"这是您点的{self.mode_reversed_mapping[mode]}榜",
                                        number=range[0] if range else 1,
                                        bot=bot, event=event, user_id=user_id, group_id=group_id)

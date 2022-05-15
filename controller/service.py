import math
import random
import time
import typing

from nonebot import logger

from ..config import Config
from ..data_source import PixivBindings, PixivDataSource, LazyIllust
from ..model import Illust
from .pkg_context import context


@context.export_singleton()
class Service:
    conf = context.require(Config)
    data_source = context.require(PixivDataSource)
    pixiv_bindings = context.require(PixivBindings)

    @staticmethod
    def _random_illust(illusts: typing.List[LazyIllust], random_method: str) -> LazyIllust:
        if random_method == "uniform":
            # 概率相等
            probability = [1 / len(illusts)] * len(illusts)
            if len(illusts) == 0:
                raise ValueError("别看了，没有的。")
        else:
            illusts = list(filter(lambda x: x.loaded, illusts))  # 只在已加载的插画中选择
            if len(illusts) == 0:
                raise ValueError("别看了，没有的。")

            if random_method == "bookmark_proportion":
                # 概率正比于书签数
                sum_bm = 0
                for x in illusts:
                    sum_bm += x.total_bookmarks + 10  # 加10平滑

                probability = [0] * len(illusts)
                for i, x in enumerate(illusts):
                    probability[i] = (x.total_bookmarks + 10) / sum_bm
            elif random_method == "view_proportion":
                # 概率正比于查看人数
                sum_view = 0
                for x in illusts:
                    sum_view += x.total_view + 10  # 加10平滑

                probability = [0] * len(illusts)
                for i, x in enumerate(illusts):
                    probability[i] = (x.total_view + 10) / sum_view
            elif random_method == "timedelta_proportion":
                # 概率正比于 exp((当前时间戳 - 画像发布时间戳) / 3e7)
                now = time.time()
                delta_time = [now - x.create_date.timestamp() for x in illusts]
                probability = [math.exp(-x * 3e-7) for x in delta_time]
                sum_poss = sum(probability)
                for i in range(len(probability)):
                    probability[i] = probability[i] / sum_poss
            else:
                raise ValueError(
                    f"illegal random_method value: {random_method}")

        for i in range(1, len(probability)):
            probability[i] = probability[i] + probability[i - 1]

        ran = random.random()

        # 二分查找
        first, last = 0, len(probability) - 1
        while first < last:
            mid = (first + last) // 2
            if probability[mid] > ran:
                last = mid
            else:
                first = mid + 1
        illust = illusts[first]

        logger.info(f"select {illust.id}")
        return illust

    RANKING_MODES = ["day", "week", "month", "day_male",
                     "day_female", "week_original", "week_rookie", "day_manga"]

    def validate_illust_ranking_args(self, mode: typing.Optional[str] = None,
                                     range: typing.Union[typing.Sequence[int], int, None] = None):
        if mode not in self.RANKING_MODES:
            raise ValueError(f"{mode}不是合法的榜单类型")

        if range is not None:
            if isinstance(range, int):
                num = range
                if num > self.conf.pixiv_ranking_fetch_item:
                    raise ValueError(
                        f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                start, end = range
                if end - start + 1 > self.conf.pixiv_ranking_max_item_per_query:
                    raise ValueError(
                        f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_query}张以下插画")
                elif start > end:
                    raise ValueError("范围不合法")
                elif end > self.conf.pixiv_ranking_fetch_item:
                    raise ValueError(
                        f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')

    async def illust_ranking(self, mode: typing.Optional[str] = None,
                             range: typing.Union[typing.Sequence[int], int, None] = None) -> typing.List[Illust]:
        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        self.validate_illust_ranking_args(mode, range)

        if isinstance(range, int):
            illusts = await self.data_source.illust_ranking(mode)
            illusts = illusts[range - 1]
        else:
            illusts = await self.data_source.illust_ranking(mode)
            illusts = illusts[range[0] - 1: range[1]]

        return [await x.get() for x in illusts]

    async def illust_detail(self, illust: int) -> Illust:
        return await self.data_source.illust_detail(illust)

    async def random_illust(self, word: str) -> Illust:
        illusts = await self.data_source.search_illust(word)
        return await self._random_illust(illusts, self.conf.pixiv_random_illust_method).get()

    async def random_user_illust(self, user: typing.Union[str, int]) -> Illust:
        if isinstance(user, str):
            users = await self.data_source.search_user(user)
            if len(users) == 0:
                raise ValueError("未找到用户")
            else:
                user = users[0].id

        illusts = await self.data_source.user_illusts(user)
        return await self._random_illust(illusts, self.conf.pixiv_random_user_illust_method).get()

    async def random_recommended_illust(self) -> Illust:
        illusts = await self.data_source.recommended_illusts()
        return await self._random_illust(illusts, self.conf.pixiv_random_recommended_illust_method).get()

    async def random_bookmark(self, qq_user_id: int = 0, pixiv_user_id: int = 0) -> Illust:
        if not pixiv_user_id and qq_user_id:
            pixiv_user_id = await self.pixiv_bindings.get_binding(qq_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise ValueError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await self.data_source.user_bookmarks(pixiv_user_id)
        return await self._random_illust(illusts, self.conf.pixiv_random_bookmark_method).get()

    async def related_illust(self, illust_id: int = 0) -> Illust:
        if illust_id == 0:
            raise ValueError("你还没有发送过请求")

        illusts = await self.data_source.related_illusts(illust_id)
        return await self._random_illust(illusts, self.conf.pixiv_random_related_illust_method).get()

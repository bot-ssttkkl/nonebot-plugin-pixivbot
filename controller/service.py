import math
import random
import time
import typing

from nonebot import logger

from ..config import Config
from ..data_source import PixivBindings, PixivDataSource, LazyIllust
from ..model import Illust, User
from ..errors import BadRequestError, QueryError
from .pkg_context import context


@context.export_singleton()
class Service:
    conf = context.require(Config)
    data_source = context.require(PixivDataSource)
    pixiv_bindings = context.require(PixivBindings)

    async def _choice_and_load(self, illusts: typing.List[LazyIllust], random_method: str, count: int) -> typing.List[Illust]:
        if count <= 0:
            raise BadRequestError("不合法的请求数量")
        if count > self.conf.pixiv_max_item_per_query:
            raise BadRequestError("数量超过单次请求上限")

        if random_method == "uniform":
            # 概率相等
            if len(illusts) == 0:
                raise QueryError("别看了，没有的。")
            probability = [1 / len(illusts)] * len(illusts)
        else:
            illusts = list(filter(lambda x: x.loaded, illusts))  # 只在已加载的插画中选择
            if len(illusts) == 0:
                raise QueryError("别看了，没有的。")

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

        choices = random.choices(illusts, probability, k=count)
        logger.info(f"choice {[x.id for x in choices]}")
        return [await x.get() for x in choices]

    async def illust_ranking(self, mode: str,
                             range: typing.Union[typing.Sequence[int], int]) -> typing.List[Illust]:
        if isinstance(range, int):
            illusts = await self.data_source.illust_ranking(mode)
            illusts = illusts[range - 1]
        else:
            illusts = await self.data_source.illust_ranking(mode)
            illusts = illusts[range[0] - 1: range[1]]

        return [await x.get() for x in illusts]

    async def illust_detail(self, illust: int) -> Illust:
        return await self.data_source.illust_detail(illust)

    async def random_illust(self, word: str, *, count: int = 1) -> Illust:
        illusts = await self.data_source.search_illust(word)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_illust_method, count)

    async def get_user(self, user: typing.Union[str, int]) -> User:
        if isinstance(user, str):
            users = await self.data_source.search_user(user)
            if len(users) == 0:
                raise QueryError("未找到用户")
            else:
                return users[0]
        else:
            return await self.data_source.user_detail(user)

    async def random_user_illust(self, user: typing.Union[str, int], *, count: int = 1) -> typing.Tuple[User, Illust]:
        user = await self.get_user(user)
        illusts = await self.data_source.user_illusts(user.id)
        illust = await self._choice_and_load(illusts, self.conf.pixiv_random_user_illust_method, count)
        return user, illust

    async def random_recommended_illust(self, *, count: int = 1) -> Illust:
        illusts = await self.data_source.recommended_illusts()
        return await self._choice_and_load(illusts, self.conf.pixiv_random_recommended_illust_method, count)

    async def random_bookmark(self, sender_user_id: int = 0, pixiv_user_id: int = 0, *, count: int = 1) -> Illust:
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await self.pixiv_bindings.get_binding(sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await self.data_source.user_bookmarks(pixiv_user_id)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_bookmark_method, count)

    async def random_related_illust(self, illust_id: int, *, count: int = 1) -> Illust:
        if illust_id == 0:
            raise BadRequestError("你还没有发送过请求")

        illusts = await self.data_source.related_illusts(illust_id)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_related_illust_method, count)

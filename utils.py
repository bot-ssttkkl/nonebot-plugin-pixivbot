import math
import random
import typing
from datetime import datetime

from nonebot.log import logger
from pixivpy3 import AppPixivAPI

from .model.Illust import Illust
from .model.Result import IllustListResult, PagedIllustListResult


async def flat_page(api: AppPixivAPI,
                    search_func: typing.Callable,
                    illust_filter: typing.Optional[typing.Callable[[Illust], bool]],
                    max_item: int = 2 ** 31,
                    max_page: int = 2 ** 31,
                    *args, **kwargs) -> IllustListResult:
    cur_page = 0
    ans = IllustListResult(illusts=[])

    # logger.debug("loading page " + str(cur_page + 1))
    raw_result = await search_func(*args, **kwargs)
    result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
    if result.error is not None:
        ans.error = result.error
        return ans

    while len(ans.illusts) < max_item and cur_page < max_page:
        for x in result.illusts:
            if illust_filter is None or illust_filter(x):
                ans.illusts.append(x)
                if len(ans.illusts) >= max_item:
                    break
        else:
            next_qs = api.parse_qs(next_url=result.next_url)
            if next_qs is None:
                break
            cur_page = cur_page + 1
            # logger.debug("loading page " + str(cur_page + 1))
            raw_result = await search_func(**next_qs)
            result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
            if result.error is not None:
                ans.error = result.error
                return ans

    return ans


def make_illust_filter(block_tags: typing.List[str],
                       min_bookmark: int = 2 ** 31,
                       min_view: int = 2 ** 31):
    def illust_filter(illust: Illust) -> bool:
        # 标签过滤
        for tag in block_tags:
            if illust.has_tag(tag):
                return False
        # 书签下限过滤
        if illust.total_bookmarks < min_bookmark:
            return False
        # 浏览量下限过滤
        if illust.total_view < min_view:
            return False
        return True

    return illust_filter


def random_illust(illusts: typing.List[Illust], random_method: str) -> Illust:
    if random_method == "bookmark_proportion":
        # 概率正比于书签数
        sum_bm = 0
        for x in illusts:
            sum_bm += x.total_bookmarks + 10  # 加10平滑
        probability = [(x.total_bookmarks + 10) / sum_bm for x in illusts]
    elif random_method == "view_proportion":
        # 概率正比于查看人数
        sum_view = 0
        for x in illusts:
            sum_view += x.total_view + 10  # 加10平滑
        probability = [(x.total_view + 10) / sum_view for x in illusts]
    elif random_method == "time_proportion":
        # 概率正比于 exp((当前时间戳 - 画像发布时间戳) / 3e7)
        now = datetime.now()
        delta_time = [(now - x.create_date).seconds for x in illusts]
        probability = [math.exp(-x * 3e-7) for x in delta_time]
        sum_poss = sum(probability)
        for i in range(len(probability)):
            probability[i] = probability[i] / sum_poss
    elif random_method == "uniform":
        # 概率相等
        probability = [1 / len(illusts)] * len(illusts)
    else:
        raise ValueError(f"illegal random_method value: {random_method}")

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
    return illusts[first]

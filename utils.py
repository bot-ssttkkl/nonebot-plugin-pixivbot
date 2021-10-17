import math
import random
import typing
from datetime import datetime

from .model.Illust import Illust


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

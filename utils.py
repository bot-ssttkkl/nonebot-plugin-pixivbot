import math
import random
import time
import typing

from .model.Illust import Illust

RANDOM_METHODS = ['bookmark_proportion', 'view_proportion', 'timedelta_proportion', 'uniform']


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
    elif random_method == "timedelta_proportion":
        # 概率正比于 exp((当前时间戳 - 画像发布时间戳) / 3e7)
        now = time.time()
        delta_time = [now - x.create_date.timestamp() for x in illusts]
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


__numerals = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
              '百': 100, '千': 1000, '万': 10000, '亿': 100000000}


def decode_chinese_integer(text: str) -> int:
    """
    将中文整数转换为int
    :param text: 中文整数
    :return: 对应int
    """
    ans = 0
    radix = 1
    for i in reversed(range(len(text))):
        if text[i] not in __numerals:
            raise ValueError
        digit = __numerals[text[i]]
        if digit >= 10:
            if digit > radix:  # 成为新的基数
                radix = digit
                if i == 0:  # 若给定字符串省略了最前面的“一”，如十三、十五……
                    ans = ans + radix
            else:
                radix = radix * digit
        else:
            ans = ans + radix * digit

    return ans


def decode_integer(text: str) -> int:
    try:
        return int(text)
    except ValueError:
        pass

    try:
        return decode_chinese_integer(text)
    except ValueError:
        pass

    raise ValueError

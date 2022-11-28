from time import time

import numpy as np

from nonebot_plugin_pixivbot.data.pixiv_repo import LazyIllust
from nonebot_plugin_pixivbot.enums import RandomIllustMethod


def uniform(illusts: list[LazyIllust]) -> np.ndarray:
    # 概率相等
    n = len(illusts)
    return np.ones(n) / n


def bookmark_proportion(illusts: list[LazyIllust]) -> np.ndarray:
    # 概率正比于书签数
    n = len(illusts)
    p = np.zeros(n)

    for i, x in enumerate(illusts):
        if x.loaded:
            p[i] = x.content.total_bookmarks + 10  # 加10平滑
        else:
            p[i] = 10

    p = np.array(p)
    return p / np.sum(p)


def view_proportion(illusts: list[LazyIllust]) -> np.ndarray:
    # 概率正比于查看人数
    n = len(illusts)
    p = np.zeros(n)

    for i, x in enumerate(illusts):
        if x.loaded:
            p[i] = x.content.total_view + 10  # 加10平滑
        else:
            p[i] = 10

    p = np.array(p)
    return p / np.sum(p)


def timedelta_proportion(illusts: list[LazyIllust]) -> np.ndarray:
    # 概率正比于 exp(归一化后的画像发布时间差)
    n = len(illusts)
    p = np.zeros(n)

    now = time()
    min_p = 0
    for i, x in enumerate(illusts):
        if x.loaded:
            p[i] = x.create_date.timestamp() - now
            if p[i] < min_p:
                min_p = p[i]
        else:
            p[i] = float("-inf")

    if min_p == 0:
        return uniform(illusts)
    else:
        p = p / -min_p  # 归一化
        p = np.exp(p)
        return p / np.sum(p)


p_gen = {
    RandomIllustMethod.uniform: uniform,
    RandomIllustMethod.bookmark_proportion: bookmark_proportion,
    RandomIllustMethod.view_proportion: view_proportion,
    RandomIllustMethod.timedelta_proportion: timedelta_proportion,
}


def roulette(illusts: list[LazyIllust], random_method: RandomIllustMethod, k: int) -> list[LazyIllust]:
    n = len(illusts)
    p = p_gen[random_method](illusts)

    if n <= k:
        return illusts

    rng = np.random.default_rng()
    winners = rng.choice(n, k, False, p)
    return [illusts[c] for c in winners]

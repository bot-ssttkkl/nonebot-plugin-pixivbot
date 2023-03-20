from typing import Iterable, List


def as_unique(iterable: Iterable) -> List:
    s = set()
    li = list()

    for x in iterable:
        if x not in s:
            li.append(x)
            s.add(x)

    return li

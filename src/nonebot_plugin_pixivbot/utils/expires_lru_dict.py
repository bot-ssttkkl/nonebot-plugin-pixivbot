from collections import OrderedDict
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import total_ordering
from heapq import heappop, heapify, heappush
from typing import TypeVar, Generic, Iterator, List, Dict, Optional, Callable

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@dataclass(frozen=True)
@total_ordering
class ExpiresNode(Generic[_KT]):
    key: _KT
    expires_time: datetime

    def __le__(self, other: "ExpiresNode"):
        return self.expires_time < other.expires_time


class ExpiresLruDict(MutableMapping[_KT, _VT], Generic[_KT, _VT]):
    def __init__(self, maxsize: int, on_cleanup: Optional[Callable[[_KT, _VT], None]] = None):
        self.maxsize = maxsize
        self.on_cleanup = on_cleanup

        self._data = OrderedDict[_KT, _VT]()
        self._expires_heap: List[ExpiresNode[_KT]] = []
        self._in_expires_heap: Dict[_KT, bool] = {}

    def _collate(self, ensure_size_for_put: bool):
        now = datetime.now(timezone.utc)
        while len(self._expires_heap) > 0 and self._expires_heap[0].expires_time <= now:
            k = self._expires_heap[0].key
            if k in self._data:
                v = self._data.pop(k)
                self.on_cleanup and self.on_cleanup(k, v)

            del self._in_expires_heap[k]
            heappop(self._expires_heap)

        if ensure_size_for_put and len(self._data) == self.maxsize:
            k, v = self._data.popitem(last=False)
            self.on_cleanup and self.on_cleanup(k, v)
            # we will not remove items from expires_heap
            # until its size reach the threshold (checked on add)

    def _collate_expires_heap(self):
        threshold = 2 * self.maxsize - 1

        if len(self._expires_heap) > threshold:
            # rebuild _expires_heap & _in_expires_heap
            expires_time_mapping = {}
            for node in self._expires_heap:
                expires_time_mapping[node.key] = expires_time_mapping[node.expires_time]

            self._expires_heap = []
            self._in_expires_heap = []
            for key in self._data:
                self._expires_heap[key] = ExpiresNode(
                    key=key,
                    expires_time=expires_time_mapping[key]
                )
                self._in_expires_heap[key] = True
            heapify(self._expires_heap)

    def add(self, key: _KT, value: _VT, expires_time: datetime):
        self._collate(True)

        if not self._in_expires_heap.get(key, False):
            heappush(self._expires_heap, ExpiresNode(key, expires_time))
            self._in_expires_heap[key] = True
        self._collate_expires_heap()

        self._data.__setitem__(key, value)

    def __setitem__(self, key: _KT, value: _VT) -> None:
        self._collate(False)
        if key not in self._data:
            raise KeyError(key)
        self._data.__setitem__(key, value)

    def __delitem__(self, key: _KT) -> None:
        self._collate(False)

        # we will not remove items from expires_heap
        # until its size reach the threshold (checked on add)
        return self._data.__delitem__(key)

    def __getitem__(self, key: _KT) -> _VT:
        self._collate(False)
        return self._data.__getitem__(key)

    def __len__(self) -> int:
        self._collate(False)
        return self._data.__len__()

    def __iter__(self) -> Iterator[_KT]:
        self._collate(False)
        return self._data.__iter__()

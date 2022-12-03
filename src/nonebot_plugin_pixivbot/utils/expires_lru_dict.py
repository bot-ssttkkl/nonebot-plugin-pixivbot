from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import total_ordering
from heapq import heappop, heapify, heappush
from typing import TypeVar, Generic, List, Optional, Callable, Union, Awaitable, AsyncIterator

from nonebot_plugin_pixivbot.utils.coros import as_async

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@dataclass(frozen=True)
@total_ordering
class ExpiresNode(Generic[_KT, _VT]):
    key: _KT
    value: _VT
    expires_time: datetime

    def __le__(self, other: "ExpiresNode"):
        return self.expires_time < other.expires_time


class AsyncExpiresLruDict(Generic[_KT, _VT]):
    def __init__(self, maxsize: int,
                 on_cleanup: Optional[Callable[[_KT, _VT], Union[None, Awaitable[None]]]] = None):
        self.maxsize = maxsize
        self.on_cleanup = as_async(on_cleanup)

        self._data = OrderedDict[_KT, ExpiresNode[_KT, _VT]]()
        self._expires_heap: List[ExpiresNode[_KT, _VT]] = []

    async def _collate(self, ensure_size_for_put: bool):
        now = datetime.now(timezone.utc)
        while len(self._expires_heap) > 0 and self._expires_heap[0].expires_time <= now:
            node = self._expires_heap[0]
            if self._data.get(node.key, None) is node:
                del self._data[node.key]
                self.on_cleanup and await self.on_cleanup(node.key, node.value)

            heappop(self._expires_heap)

        if ensure_size_for_put and len(self._data) == self.maxsize:
            key, node = self._data.popitem(last=False)
            self.on_cleanup and await self.on_cleanup(key, node.value)
            # we will not remove items from expires_heap
            # until its size reach the threshold (checked on add)

    def _collate_expires_heap(self):
        threshold = 2 * self.maxsize - 1

        if len(self._expires_heap) > threshold:
            # rebuild _expires_heap
            self._expires_heap = []
            for node in self._data.values():
                self._expires_heap.append(node)
            heapify(self._expires_heap)

    async def add(self, key: _KT, value: _VT, expires_time: datetime):
        await self._collate(True)

        if self._data.__contains__(key):
            raise KeyError(key)

        node = ExpiresNode(key, value, expires_time)
        self._data.__setitem__(key, node)
        heappush(self._expires_heap, node)

        self._collate_expires_heap()

    async def set(self, key: _KT, value: _VT) -> None:
        await self._collate(False)
        if key not in self._data:
            raise KeyError(key)

        node = self._data.__getitem__(key)
        self._data[key] = ExpiresNode(key, value, node.expires_time)

    async def pop(self, key: _KT) -> _VT:
        await self._collate(False)

        # we will not remove items from expires_heap
        # until its size reach the threshold (checked on add)
        return self._data.pop(key)

    async def get(self, key: _KT) -> _VT:
        await self._collate(False)
        node = self._data.get(key, None)
        return node.value if node else None

    async def len(self) -> int:
        await self._collate(False)
        return self._data.__len__()

    async def iter(self) -> AsyncIterator[_KT]:
        await self._collate(False)
        for k in self._data.__iter__():
            yield k

    async def contains(self, key: _KT) -> bool:
        await self._collate(False)
        return self._data.__contains__(key)

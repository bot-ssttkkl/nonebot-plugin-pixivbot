import asyncio
from inspect import isawaitable
from typing import Callable, Union, Awaitable


class DataSourceLifecycleMixin:
    def __init__(self, *args, **kwargs):
        self._on_initialized_callbacks = []
        self._on_closed_callbacks = []

    def on_initialized(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_initialized_callbacks.append(func)

    def on_closed(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_closed_callbacks.append(func)

    async def fire_initialized(self):
        fut = filter(isawaitable, (x() for x in self._on_initialized_callbacks))
        await asyncio.gather(*fut)

    async def fire_closed(self):
        fut = filter(isawaitable, (x() for x in self._on_closed_callbacks))
        await asyncio.gather(*fut)

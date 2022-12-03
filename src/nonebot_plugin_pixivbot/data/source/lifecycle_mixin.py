import asyncio
from inspect import isawaitable
from typing import Callable, Union, Awaitable

from nonebot import logger


class DataSourceLifecycleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_initializing_callbacks = []
        self._on_initialized_callbacks = []
        self._on_closing_callbacks = []
        self._on_closed_callbacks = []

    def on_initializing(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_initializing_callbacks.append(func)

    def on_initialized(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_initialized_callbacks.append(func)

    def on_closing(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_closing_callbacks.append(func)

    def on_closed(self, func: Callable[[], Union[None, Awaitable[None]]]):
        self._on_closed_callbacks.append(func)

    async def _fire_initializing(self):
        logger.trace("[data source] Firing initializing event")
        fut = filter(isawaitable, (x() for x in self._on_initializing_callbacks))
        await asyncio.gather(*fut)

    async def _fire_initialized(self):
        logger.trace("[data source] Firing initialized event")
        fut = filter(isawaitable, (x() for x in self._on_initialized_callbacks))
        await asyncio.gather(*fut)

    async def _fire_closing(self):
        logger.trace("[data source] Firing closing event")
        fut = filter(isawaitable, (x() for x in self._on_closing_callbacks))
        await asyncio.gather(*fut)

    async def _fire_closed(self):
        logger.trace("[data source] Firing closed event")
        fut = filter(isawaitable, (x() for x in self._on_closed_callbacks))
        await asyncio.gather(*fut)

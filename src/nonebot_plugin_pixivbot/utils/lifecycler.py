"""
为了让生命周期严格呈现以下模式：
on_startup -> on_bot_connect -> on_bot_disconnect -> on_shutdown
"""

import asyncio
from asyncio import create_task
from inspect import isawaitable

from nonebot import Bot, get_driver, logger

_on_startup_callback = []
_on_bot_connect_callback = []
_on_bot_disconnect_callback = []
_on_shutdown_callback = []

# 使用协程形式的Event是因为on_shutdown在on_bot_connected之前，如果用线程形式的Event会死锁
_startup = asyncio.Event()
_shutdown = asyncio.Event()

_mutex = asyncio.Lock()

_connected_bot = set()

_no_bot_connect = asyncio.Event()
_no_bot_connect.set()


# 注册回调不加锁是因为没有多线程场景

def on_startup(replay: bool = False, first: bool = False):
    def decorator(func):
        if replay and _startup.is_set():
            logger.trace("[lifecycler] replaying on_startup")
            x = func()
            if isawaitable(x):
                asyncio.create_task(x)
        if first:
            _on_startup_callback.insert(0, func)
        else:
            _on_startup_callback.append(func)
        return func

    return decorator


def on_bot_connect(replay: bool = False, first: bool = False):
    def decorator(func):
        if replay:
            for bot in _connected_bot:
                logger.trace(f"[lifecycler] replaying on_bot_connect with {bot}")
                x = func(bot)
                if isawaitable(x):
                    asyncio.create_task(x)
        if first:
            _on_bot_connect_callback.insert(0, func)
        else:
            _on_bot_connect_callback.append(func)
        return func

    return decorator


def on_bot_disconnect(first: bool = False):
    def decorator(func):
        if first:
            _on_bot_disconnect_callback.insert(0, func)
        else:
            _on_bot_disconnect_callback.append(func)
        return func

    return decorator


def on_shutdown(first: bool = False):
    def decorator(func):
        if first:
            _on_shutdown_callback.append(func)
        else:
            _on_shutdown_callback.append(func)
        return func

    return decorator


async def _fire_startup():
    await _mutex.acquire()
    try:
        logger.trace("[lifecycler] firing on startup")
        cors = [f() for f in _on_startup_callback]
        cors = [create_task(x) for x in cors if isawaitable(x)]
        if len(cors) > 0:
            await asyncio.gather(*cors)

        _startup.set()
    finally:
        _mutex.release()


async def _fire_bot_connect(bot: Bot):
    await _startup.wait()
    await _mutex.acquire()
    try:
        logger.trace(f"[lifecycler] firing on bot {bot} connect")
        cors = [f(bot) for f in _on_bot_connect_callback]
        cors = [create_task(x) for x in cors if isawaitable(x)]
        if len(cors) > 0:
            await asyncio.gather(*cors)

        _connected_bot.add(bot)
        _no_bot_connect.clear()
    finally:
        _mutex.release()


async def _fire_bot_disconnect(bot: Bot):
    await _startup.wait()
    await _mutex.acquire()
    try:
        logger.trace(f"[lifecycler] firing on bot {bot} disconnect")
        cors = [f(bot) for f in _on_bot_disconnect_callback]
        cors = [create_task(x) for x in cors if isawaitable(x)]
        if len(cors) > 0:
            await asyncio.gather(*cors)

        _connected_bot.remove(bot)
        if not _connected_bot:
            _no_bot_connect.set()
    finally:
        _mutex.release()


async def _fire_shutdown():
    await _no_bot_connect.wait()
    await _mutex.acquire()
    try:
        logger.trace(f"[lifecycler] firing on shutdown")
        cors = [f() for f in _on_shutdown_callback]
        cors = [create_task(x) for x in cors if isawaitable(x)]
        if len(cors) > 0:
            await asyncio.gather(*cors)
    finally:
        _mutex.release()


_driver = get_driver()
_driver.on_startup(_fire_startup)
_driver.on_bot_connect(_fire_bot_connect)
_driver.on_bot_disconnect(_fire_bot_disconnect)
_driver.on_shutdown(_fire_shutdown)

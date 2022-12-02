import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TypeVar, Generic, Callable, Awaitable, Any

from nonebot import logger

T = TypeVar("T")


class ScopedRegistry(Generic[T]):
    def __init__(self, createfunc: Callable[[], Awaitable[T]],
                 disposefunc: Callable[[T], Awaitable[None]],
                 scopefunc: Callable[[], Any]):
        self.createfunc = createfunc
        self.disposefunc = disposefunc
        self.scopefunc = scopefunc
        self.registry = {}

    async def get_or_create(self) -> T:
        scope = self.scopefunc()
        if scope not in self.registry:
            x = await self.createfunc()
            self.registry[scope] = x

        return self.registry[scope]

    def get(self) -> T:
        return self.registry[self.scopefunc()]

    def has(self) -> bool:
        """Return True if an object is present in the current scope."""

        return self.scopefunc() in self.registry

    def set(self, obj: T):
        """Set the value for the current scope."""

        self.registry[self.scopefunc()] = obj

    async def clear(self):
        """Clear the current scope, if any."""

        try:
            obj = self.registry.pop(self.scopefunc())
            await self.disposefunc(obj)
        except KeyError:
            pass


T_SESS = TypeVar("T_SESS")


class SessionScopeMixin(Generic[T_SESS], ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_scope_id = ContextVar(f"pixivbot_session_scope_id_{id(self)}")
        self._session_registry = ScopedRegistry[T_SESS](createfunc=self._start_session,
                                                        disposefunc=self._close_session,
                                                        scopefunc=self._session_scope_id.get)

    def session(self):
        return self._session_registry.get()

    @abstractmethod
    async def _start_session(self) -> T_SESS:
        ...

    @abstractmethod
    async def _close_session(self, session: T_SESS):
        ...

    @asynccontextmanager
    async def session_scope(self):
        session_id = uuid.uuid4()
        t_token = self._session_scope_id.set(session_id)
        session = await self._session_registry.get_or_create()

        logger.trace(f"new session scope {session_id}")
        try:
            yield session
        finally:
            await self._session_registry.clear()
            self._session_scope_id.reset(t_token)

            logger.trace(f"removed session scope {session_id}")

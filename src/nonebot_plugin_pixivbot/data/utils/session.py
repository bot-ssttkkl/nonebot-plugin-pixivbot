import contextvars
from contextlib import asynccontextmanager, AbstractAsyncContextManager

from nonebot_plugin_orm import get_session
from sqlalchemy.ext.asyncio import AsyncSession

_pixivbot_current_session = contextvars.ContextVar("pixivbot_current_session")


@asynccontextmanager
async def use_pixivbot_session() -> AbstractAsyncContextManager[AsyncSession]:
    try:
        yield _pixivbot_current_session.get()
    except LookupError:
        session = get_session()
        token = _pixivbot_current_session.set(session)

        yield session

        await session.close()
        _pixivbot_current_session.reset(token)

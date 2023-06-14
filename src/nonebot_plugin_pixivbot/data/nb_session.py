from typing import Optional

from nonebot_plugin_datastore.db import get_engine
from nonebot_plugin_session import Session
from nonebot_plugin_session.model import get_or_add_session_model, SessionModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..global_context import context


@context.register_singleton()
class NbSessionRepo:
    async def get_id(self, session: Session) -> int:
        async with AsyncSession(get_engine()) as db_sess:
            model = await get_or_add_session_model(session, db_sess)
            return model.id

    async def get_session(self, session_id: int) -> Optional[Session]:
        async with AsyncSession(get_engine()) as db_sess:
            model = await db_sess.get(SessionModel, session_id)
            if model is None:
                return None
            return model.session

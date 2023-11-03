from typing import Optional

from nonebot_plugin_session import Session
from nonebot_plugin_session_orm import get_session_persist_id, get_session_by_persist_id
from sqlalchemy.exc import NoResultFound

from ..global_context import context


@context.register_singleton()
class NbSessionRepo:
    async def get_id(self, session: Session) -> int:
        return await get_session_persist_id(session)

    async def get_session(self, session_id: int) -> Optional[Session]:
        try:
            return await get_session_by_persist_id(session_id)
        except NoResultFound:
            return None

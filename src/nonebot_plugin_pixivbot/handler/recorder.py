from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Mapping, Any, Type, NamedTuple, Sequence

from cachetools import TTLCache
from nonebot.internal.adapter import Event
from nonebot_plugin_session import Session, SessionIdType

from .pkg_context import context
from ..config import Config
from ..model.message import IllustMessagesModel
from ..service.postman import Postman

if TYPE_CHECKING:
    from .base import Handler

conf = context.require(Config)


class Req(NamedTuple):
    handler_type: Type["Handler"]
    args: Sequence[Any]
    kwargs: Mapping[str, Any]


class Resp(NamedTuple):
    illust_id: int


@context.root.register_singleton()
class Recorder:
    def __init__(self, max_req_size: int = 65535,
                 max_resp_size: int = 65535):
        self._reqs = TTLCache[str, Req](maxsize=max_req_size,
                                        ttl=conf.pixiv_query_expires_in)
        self._resps = TTLCache[str, Resp](maxsize=max_resp_size,
                                          ttl=conf.pixiv_query_expires_in)

        self.max_req_size = max_req_size
        self.max_resp_size = max_resp_size

    def record_req(self, record: Req, session: Session):
        key = session.get_id(SessionIdType.GROUP)
        self._reqs[key] = record

    def get_req(self, session: Session) -> Optional[Req]:
        key = session.get_id(SessionIdType.GROUP)
        if key in self._reqs:
            req = self._reqs[key]
            return req
        else:
            return None

    def record_resp(self, illust_id: int, session: Session):
        key = session.get_id(SessionIdType.GROUP)
        self._resps[key] = Resp(illust_id)

    def get_resp(self, session: Session) -> Optional[int]:
        key = session.get_id(SessionIdType.GROUP)
        if key in self._resps:
            rec = self._resps[key]
            return rec.illust_id
        else:
            return None


origin_postman = context.require(Postman)


@context.bind_singleton_to(Postman, origin_postman)
class RecordPostman:
    def __init__(self, delegation: Postman):
        self.delegation = delegation

    async def post_illusts(self, model: IllustMessagesModel, session: Session, event: Optional[Event] = None):
        recorder = context.require(Recorder)
        await self.delegation.post_illusts(model, session, event)
        if len(model.messages) == 1:
            recorder.record_resp(model.messages[0].id, session)

    def __getattr__(self, name: str):
        return getattr(self.delegation, name)

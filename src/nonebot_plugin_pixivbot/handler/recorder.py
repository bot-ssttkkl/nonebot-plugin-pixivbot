from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Mapping, Any, Type, NamedTuple, Sequence

from cachetools import TTLCache

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.model import PostIdentifier, T_UID, T_GID
from nonebot_plugin_pixivbot.model.message import IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from .pkg_context import context

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
        self._reqs = TTLCache[PostIdentifier[T_UID, T_GID], Req](maxsize=max_req_size,
                                                                 ttl=conf.pixiv_query_expires_in)
        self._resps = TTLCache[PostIdentifier[T_UID, T_GID], Resp](maxsize=max_resp_size,
                                                                   ttl=conf.pixiv_query_expires_in)

        self.max_req_size = max_req_size
        self.max_resp_size = max_resp_size

    @staticmethod
    def _key_fallback(key: PostIdentifier[T_UID, T_GID]) -> Optional[PostIdentifier[T_UID, T_GID]]:
        if key.user_id is not None and key.group_id is not None:
            return PostIdentifier[T_UID, T_GID](key.adapter, None, key.group_id)
        else:
            return None

    def record_req(self, record: Req, key: PostIdentifier[T_UID, T_GID]):
        self._reqs[key] = record

    def get_req(self, key: PostIdentifier[T_UID, T_GID]) -> Optional[Req]:
        if key in self._reqs:
            req = self._reqs[key]
            return req
        else:
            key = self._key_fallback(key)
            if key is not None:
                return self.get_req(key)
            else:
                return None

    def record_resp(self, illust_id: int, key: PostIdentifier[T_UID, T_GID]):
        self._resps[key] = Resp(illust_id)

    def get_resp(self, key: PostIdentifier[T_UID, T_GID]) -> Optional[int]:
        if key in self._resps:
            rec = self._resps[key]
            return rec.illust_id
        else:
            key = self._key_fallback(key)
            if key is not None:
                return self.get_resp(key)
            else:
                return None


origin_postman_mgr = context.require(PostmanManager)


@context.bind_singleton_to(PostmanManager, origin_postman_mgr)
class RecordPostmanManager:
    def __init__(self, delegation: PostmanManager):
        self.delegation = delegation

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination[T_UID, T_GID]):
        recorder = context.require(Recorder)
        await self.delegation.send_illusts(model, post_dest=post_dest)
        if len(model.messages) == 1:
            recorder.record_resp(model.messages[0].id, post_dest.identifier)

    def __getattr__(self, name: str):
        return getattr(self.delegation, name)

from __future__ import annotations

from typing import Optional

from cachetools import TTLCache

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.model import PostIdentifier, T_UID, T_GID
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from .pkg_context import context


class Req:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, **kwargs):
        actual_kwargs = self.kwargs.copy()
        for x, y in kwargs.items():
            actual_kwargs[x] = y

        return self.func(*self.args, **actual_kwargs)


class Resp:
    def __init__(self, illust_id: int):
        self.illust_id = illust_id


@context.inject
@context.root.register_singleton()
class Recorder:
    conf = Inject(Config)

    def __init__(self, max_req_size: int = 65535,
                 max_resp_size: int = 65535):
        self._reqs = TTLCache[PostIdentifier[T_UID, T_GID], Req](maxsize=max_req_size,
                                                                 ttl=self.conf.pixiv_query_expires_in)
        self._resps = TTLCache[PostIdentifier[T_UID, T_GID], Resp](maxsize=max_resp_size,
                                                                   ttl=self.conf.pixiv_query_expires_in)

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


@context.inject
@context.bind_singleton_to(PostmanManager, context.require(PostmanManager))
class RecordPostmanManager:
    recorder = Inject(Recorder)

    def __init__(self, delegation: PostmanManager):
        self.delegation = delegation

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination[T_UID, T_GID]):
        await self.delegation.send_illust(model, post_dest=post_dest)
        self.recorder.record_resp(model.id, post_dest.identifier)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination[T_UID, T_GID]):
        await self.delegation.send_illusts(model, post_dest=post_dest)
        if len(model.messages) == 1:
            self.recorder.record_resp(model.messages[0].id, post_dest.identifier)

    def __getattr__(self, name: str):
        return getattr(self.delegation, name)

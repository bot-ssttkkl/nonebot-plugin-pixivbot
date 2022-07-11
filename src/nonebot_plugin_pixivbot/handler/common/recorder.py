import time
from collections import OrderedDict
from typing import Optional, TypeVar, Generic

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.postman import PostDestination

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]
ID = PostIdentifier[UID, GID]


class Req(Generic[UID, GID]):
    def __init__(self, handler: 'Handler[UID, GID]',
                 *args, **kwargs):
        self.timestamp = 0
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()

    def __call__(self, *, post_dest: PD, **kwargs):
        actual_kwargs = self.kwargs
        for x, y in kwargs.items():
            actual_kwargs[x] = y

        return self.handler.handle(*self.args, post_dest=post_dest, **actual_kwargs)


class Resp:
    def __init__(self, illust_id: int):
        self.timestamp = 0
        self.illust_id = illust_id
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()


@context.register_singleton()
class Recorder(Generic[UID, GID]):
    conf = context.require(Config)

    def __init__(self):
        self._reqs = OrderedDict[ID, Req[UID, GID]]()
        self._resps = OrderedDict[ID, Resp]()

    @staticmethod
    def _key_fallback(key: ID) -> Optional[ID]:
        if key.user_id is not None and key.group_id is not None:
            return ID(None, key.group_id)
        else:
            return None

    def _pop_expired_req(self):
        now = time.time()
        while len(self._reqs) > 0:
            key, req = next(iter(self._reqs.items()))
            if now - req.timestamp > self.conf.pixiv_query_expires_in:
                self._reqs.popitem(last=False)
                logger.info(f"expired req popped: ({key})")
            else:
                break

    def record_req(self, record: Req, key: ID):
        self._pop_expired_req()
        if key in self._reqs:
            self._reqs.move_to_end(key)
        self._reqs[key] = record

    def get_req(self, key: ID) -> Optional[Req]:
        self._pop_expired_req()
        if key in self._reqs:
            req = self._reqs[key]
            req.refresh()
            self._reqs.move_to_end(key)
            return req
        else:
            key = self._key_fallback(key)
            if key is not None:
                return self.get_req(key)
            else:
                return None

    def _pop_expired_resp(self):
        now = time.time()
        while len(self._resps) > 0:
            key, rec = next(iter(self._resps.items()))
            if now - rec.timestamp > self.conf.pixiv_query_expires_in:
                self._resps.popitem(last=False)
                logger.info(f"expired illust popped: ({key})")
            else:
                break

    def record_resp(self, illust_id: int, key: ID):
        self._pop_expired_resp()
        if key in self._resps:
            self._resps.move_to_end(key)
        self._resps[key] = Resp(illust_id)

    def get_resp(self, key: ID) -> Optional[int]:
        self._pop_expired_resp()
        if key in self._resps:
            rec = self._resps[key]
            return rec.illust_id
        else:
            key = self._key_fallback(key)
            if key is not None:
                return self.get_resp(key)
            else:
                return None

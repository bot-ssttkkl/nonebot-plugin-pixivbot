from __future__ import annotations

import time
from collections import OrderedDict
from typing import Optional, TypeVar, TYPE_CHECKING

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

if TYPE_CHECKING:
    pass

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]
ID = PostIdentifier[UID, GID]


class Req:
    def __init__(self, func,
                 *args, **kwargs):
        self.timestamp = 0
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()

    def __call__(self, **kwargs):
        actual_kwargs = self.kwargs.copy()
        for x, y in kwargs.items():
            actual_kwargs[x] = y

        return self.func(*self.args, **actual_kwargs)


class Resp:
    def __init__(self, illust_id: int):
        self.timestamp = 0
        self.illust_id = illust_id
        self.refresh()

    def refresh(self):
        self.timestamp = time.time()


@context.inject
@context.register_singleton()
class Recorder:
    conf: Config

    def __init__(self, max_req_size: int = 65535,
                 max_resp_size: int = 65535):
        self._reqs = OrderedDict[ID, Req]()
        self._resps = OrderedDict[ID, Resp]()

        self.max_req_size = max_req_size
        self.max_resp_size = max_resp_size

    @staticmethod
    def _key_fallback(key: ID) -> Optional[ID]:
        if key.user_id is not None and key.group_id is not None:
            return ID(key.adapter, None, key.group_id)
        else:
            return None

    def _collate_req(self, ensure_size_for_put: bool):
        now = time.time()
        while len(self._reqs) > 0:
            key, req = next(iter(self._reqs.items()))
            if now - req.timestamp > self.conf.pixiv_query_expires_in:
                self._reqs.popitem(last=False)
                logger.info(f"popped expired req: ({key})")
            else:
                break

        if ensure_size_for_put and len(self._reqs) == self.max_req_size:
            key, req = self._reqs.popitem(last=False)
            logger.info(f"popped first req: ({key})")

    def record_req(self, record: Req, key: ID):
        self._collate_req(True)
        if key in self._reqs:
            self._reqs.move_to_end(key)
        self._reqs[key] = record

    def get_req(self, key: ID) -> Optional[Req]:
        self._collate_req(False)
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

    def _collate_resp(self, ensure_size_for_put: bool):
        now = time.time()
        while len(self._resps) > 0:
            key, resp = next(iter(self._resps.items()))
            if now - resp.timestamp > self.conf.pixiv_query_expires_in:
                self._resps.popitem(last=False)
                logger.info(f"popped expired resp illust: ({key})")
            else:
                break

        if ensure_size_for_put and len(self._resps) == self.max_resp_size:
            key, resp = self._resps.popitem(last=False)
            logger.info(f"popped first resp illust: ({key})")

    def record_resp(self, illust_id: int, key: ID):
        self._collate_resp(True)
        if key in self._resps:
            self._resps.move_to_end(key)
        self._resps[key] = Resp(illust_id)

    def get_resp(self, key: ID) -> Optional[int]:
        self._collate_resp(False)
        if key in self._resps:
            rec = self._resps[key]
            return rec.illust_id
        else:
            key = self._key_fallback(key)
            if key is not None:
                return self.get_resp(key)
            else:
                return None

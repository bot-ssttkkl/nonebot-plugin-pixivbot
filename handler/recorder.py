import time
import typing

from collections import OrderedDict
from nonebot import logger

from .pkg_context import context
from .req_resp import Req, Resp


@context.register_singleton()
class Recorder:
    def __init__(self, expires_in: int = 10*60):
        self._reqs = OrderedDict()
        self._resps = OrderedDict()
        self.expires_in = expires_in

    def _pop_expired_req(self):
        now = time.time()
        while len(self._reqs) > 0:
            (user_id, group_id), req = next(iter(self._reqs.items()))
            if now - req.timestamp > self.expires_in:
                self._reqs.popitem(last=False)
                logger.info(f"expired req popped: ({user_id}, {group_id})")
            else:
                break

    def record_req(self, record: Req,
                   *, user_id: typing.Optional[int] = None,
                   group_id: typing.Optional[int] = None):
        self._pop_expired_req()
        if (user_id, group_id) in self._reqs:
            self._reqs.move_to_end((user_id, group_id))
        self._reqs[(user_id, group_id)] = record

    def get_req(self, *, user_id: typing.Optional[int] = None,
                group_id: typing.Optional[int] = None) -> typing.Optional[Req]:
        self._pop_expired_req()
        if (user_id, group_id) in self._reqs:
            req = self._reqs[(user_id, group_id)]
            req.refresh()
            self._reqs.move_to_end((user_id, group_id))
            return req
        elif user_id and group_id:  # 获取上一条群订阅的请求
            return self.get_req(group_id=group_id)
        else:
            return None

    def _pop_expired_resp(self):
        now = time.time()
        while len(self._resps) > 0:
            (user_id, group_id), rec = next(iter(self._resps.items()))
            if now - rec.timestamp > self.expires_in:
                self._resps.popitem(last=False)
                logger.info(f"expired illust popped: ({user_id}, {group_id})")
            else:
                break

    def record_resp(self, illust_id: int, *,
                    user_id: typing.Optional[int] = None,
                    group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._resps:
            self._resps.move_to_end((user_id, group_id))
        self._resps[(user_id, group_id)] = Resp(illust_id)

    def get_resp(self,  *,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._resps:
            rec = self._resps[(user_id, group_id)]
            return rec.illust_id
        elif user_id is not None and group_id is not None:  # 获取上一条群订阅的响应
            return self.get_resp(group_id=group_id)
        else:
            return 0

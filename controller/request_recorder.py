from collections import OrderedDict
import time
import typing

from nonebot import logger

from .pkg_context import context

@context.register_singleton()
class RequestRecorder:
    def __init__(self, expires_in: int = 10*60):
        self._prev_req_func = OrderedDict()
        self._prev_resp_illust_id = OrderedDict()
        self.expires_in = expires_in

    def _pop_expired_req(self):
        now = time.time()
        while len(self._prev_req_func) > 0:
            (user_id, group_id), (timestamp, _) = next(
                iter(self._prev_req_func.items()))
            if now - timestamp > self.expires_in:
                self._prev_req_func.popitem(last=False)
                logger.info(f"popped expired req: ({user_id}, {group_id})")
            else:
                break

    def push_req(self, func: typing.Callable, *,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None):
        self._pop_expired_req()
        if (user_id, group_id) in self._prev_req_func:
            self._prev_req_func.move_to_end((user_id, group_id))
        self._prev_req_func[(user_id, group_id)] = time.time(), func

    def get_req(self,  *,
                user_id: typing.Optional[int] = None,
                group_id: typing.Optional[int] = None) -> typing.Callable:
        self._pop_expired_req()
        if (user_id, group_id) in self._prev_req_func:
            (_, func) = self._prev_req_func[(user_id, group_id)]
            self._prev_req_func[(user_id, group_id)] = time.time(), func
            self._prev_req_func.move_to_end((user_id, group_id))
            return func
        elif user_id is not None and group_id is not None:  # 获取上一条群订阅的请求
            return self._get_req(group_id=group_id)
        else:
            return None

    def _pop_expired_resp(self):
        now = time.time()
        while len(self._prev_resp_illust_id) > 0:
            (user_id, group_id), (timestamp, _) = next(
                iter(self._prev_resp_illust_id.items()))
            if now - timestamp > self.expires_in:
                self._prev_resp_illust_id.popitem(last=False)
                logger.info(f"popped expired resp: ({user_id}, {group_id})")
            else:
                break

    def push_resp(self, illust_id: int, *,
                  user_id: typing.Optional[int] = None,
                  group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._prev_resp_illust_id:
            self._prev_resp_illust_id.move_to_end((user_id, group_id))
        self._prev_resp_illust_id[(user_id, group_id)] = time.time(), illust_id

    def get_resp(self,  *,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._prev_resp_illust_id:
            (_, illust_id) = self._prev_resp_illust_id[(user_id, group_id)]
            return illust_id
        elif user_id is not None and group_id is not None:  # 获取上一条群订阅的响应
            return self._get_resp(group_id=group_id)
        else:
            return 0

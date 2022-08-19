from typing import Optional

import pytest

from tests import MyTest


class FakeRecorderMixin(MyTest):
    @pytest.fixture
    def fake_recorder(self):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.common.recorder import Recorder, Req
        from nonebot_plugin_pixivbot.model import PostIdentifier

        @context.bind_singleton_to(Recorder)
        class FakeRecorder:
            def __init__(self):
                self.req = {}
                self.resp = {}

            def get_req(self, key: PostIdentifier[int, int]) -> Optional[Req]:
                return self.req.get(key, None)

            def record_req(self, record: Req, key: PostIdentifier[int, int]):
                self.req[key] = record

            def get_resp(self, key: PostIdentifier[int, int]) -> Optional[int]:
                return self.resp.get(key, None)

            def record_resp(self, illust_id: int, key: PostIdentifier[int, int]):
                self.resp[key] = illust_id

        return FakeRecorder

from typing import TypeVar, Optional

import pytest

from tests import MyTest


class FakePixivAccountBinderMixin(MyTest):
    @pytest.fixture(autouse=True)
    def fake_pixiv_account_binder(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import PixivBinding
        from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder

        UID = TypeVar("UID")

        @context.bind_singleton_to(PixivAccountBinder)
        class FakePixivAccountBinder:
            def __init__(self):
                self.bindings = {}

            async def bind(self, adapter: str, user_id: UID, pixiv_user_id: int):
                binding = PixivBinding(adapter=adapter, user_id=user_id, pixiv_user_id=pixiv_user_id)
                self.bindings[(adapter, user_id)] = binding

            async def unbind(self, adapter: str, user_id: UID) -> bool:
                if (adapter, user_id) in self.bindings:
                    del self.bindings[(adapter, user_id)]
                    return True
                else:
                    return False

            async def get_binding(self, adapter: str, user_id: UID) -> Optional[int]:
                binding = self.bindings.get((adapter, user_id), None)
                if binding:
                    return binding.pixiv_user_id
                else:
                    return None

        return FakePixivAccountBinder

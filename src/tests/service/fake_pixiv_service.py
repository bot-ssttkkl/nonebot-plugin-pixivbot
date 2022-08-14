from typing import Union

import pytest

from tests import MyTest


class FakePixivServiceMixin(MyTest):
    @pytest.fixture(autouse=True)
    def fake_pixiv_service(self):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import User
        from nonebot_plugin_pixivbot.service.pixiv_service import PixivService

        @context.bind_singleton_to(PixivService)
        class FakePixivService:
            async def get_user(self, user: Union[str, int]) -> User:
                if isinstance(user, str):
                    return User(id=54321, name=user, account=user)
                else:
                    return User(id=user, name="TestUser", account="test_user")

        return FakePixivService
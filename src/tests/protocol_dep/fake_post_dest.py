from typing import Optional

import pytest

from tests import MyTest


class FakePostDestinationMixin(MyTest):
    @pytest.fixture
    def FakePostDestination(self, load_pixivbot):
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.model import PostIdentifier

        class FakePostDestination(PostDestination[int, int]):
            def __init__(self, user_id: Optional[int], group_id: Optional[int]):
                self._identifier = PostIdentifier("test", user_id, group_id)

            @property
            def identifier(self) -> PostIdentifier[int, int]:
                return self._identifier

            def normalized(self) -> "PostDestination[int, int]":
                return self

        return FakePostDestination


class FakePostDestinationFactoryManagerMixin(FakePostDestinationMixin, MyTest):
    @pytest.fixture(autouse=True)
    def FakePostDestinationFactoryManager(self, load_pixivbot, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination, PostDestinationFactoryManager

        from nonebot import Bot
        from nonebot.internal.adapter import Event

        @context.bind_singleton_to(PostDestinationFactoryManager)
        class FakePostDestinationFactoryManager:
            def build(self, bot: Bot, user_id: Optional[int], group_id: Optional[int]) -> PostDestination[int, int]:
                return FakePostDestination(user_id, group_id)

            def from_event(self, bot: Bot, event: Event) -> PostDestination[int, int]:
                return FakePostDestination(int(event.get_user_id()), None)

        return FakePostDestinationFactoryManager

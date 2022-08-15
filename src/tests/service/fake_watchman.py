from typing import List, Dict, Any

import pytest
from frozendict import frozendict

from tests import MyTest


class FakeWatchmanMixin(MyTest):
    @pytest.fixture
    async def fake_watchman(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask
        from nonebot_plugin_pixivbot.service.watchman import Watchman
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

        @context.bind_singleton_to(Watchman)
        class FakeWatchman:
            def __init__(self):
                self.tasks = {}

            async def watch(self, type: WatchType,
                            kwargs: Dict[str, Any],
                            subscriber: PostDestination[int, int]):
                key = (subscriber.identifier, type, frozendict(kwargs))
                self.tasks[key] = WatchTask(
                    type=type,
                    kwargs=kwargs,
                    subscriber=subscriber.identifier
                )

            async def unwatch(self, type: WatchType,
                              kwargs: Dict[str, Any],
                              subscriber: PostIdentifier[int, int]) -> bool:
                key = (subscriber, type, frozendict(kwargs))
                if key in self.tasks:
                    del self.tasks[key]
                    return True
                else:
                    return False

            async def get_by_subscriber(self, subscriber: PostIdentifier[int, int]) -> List[WatchTask]:
                keys = list(filter(lambda x: x[0] == subscriber, self.tasks.keys()))
                li = []
                for k in keys:
                    li.append(self.tasks[k])
                return li

        return FakeWatchman

from typing import Dict, Any, AsyncGenerator

import pytest

from tests import MyTest


class FakeWatchmanMixin(MyTest):
    @pytest.fixture(autouse=True)
    async def FakeWatchman(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask
        from nonebot_plugin_pixivbot.service.watchman import Watchman
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination

        @context.bind_singleton_to(Watchman)
        class FakeWatchman:
            def __init__(self):
                self.tasks = {}
                self.code_gen = 0

            async def watch(self, type_: WatchType,
                            kwargs: Dict[str, Any],
                            subscriber: PostDestination[int, int]) -> bool:
                self.code_gen += 1
                code = self.code_gen
                self.tasks[code] = WatchTask(
                    code=code,
                    type=type_,
                    kwargs=kwargs,
                    subscriber=subscriber.identifier
                )
                return True

            async def unwatch(self, subscriber: PostIdentifier[int, int], code: int) -> bool:
                if code in self.tasks:
                    del self.tasks[code]
                    return True
                else:
                    return False

            async def unwatch_all_by_subscriber(self, subscriber: PostIdentifier[int, int]):
                keys = set()
                for k, v in self.tasks.items():
                    if v.subscriber == subscriber:
                        keys.add(k)

                for k in keys:
                    del self.tasks[k]

            async def get_by_subscriber(self, subscriber: PostIdentifier[int, int]) -> AsyncGenerator[WatchTask, None]:
                for k, v in self.tasks.items():
                    if v.subscriber == subscriber:
                        yield v

        return FakeWatchman

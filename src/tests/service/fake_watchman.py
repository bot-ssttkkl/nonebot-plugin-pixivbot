from typing import Dict, Any, AsyncGenerator

import pytest

from tests import MyTest


class FakeWatchmanMixin(MyTest):
    @pytest.fixture(autouse=True)
    async def FakeWatchman(self, load_pixivbot):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.model import PostIdentifier, WatchType, WatchTask
        from nonebot_plugin_pixivbot.service.watchman import Watchman
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.data.utils.shortuuid import gen_code

        @context.bind_singleton_to(Watchman)
        class FakeWatchman:
            def __init__(self):
                self.tasks = {}

            async def watch(self, type_: WatchType,
                            kwargs: Dict[str, Any],
                            subscriber: PostDestination[int, int]) -> bool:
                self.code_gen += 1
                code = gen_code()
                self.tasks[code] = WatchTask(
                    code=code,
                    type=type_,
                    kwargs=kwargs,
                    subscriber=subscriber.identifier
                )
                return True

            async def unwatch(self, subscriber: PostIdentifier[int, int], code: str) -> bool:
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

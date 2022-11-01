from typing import Sequence, List, Union, AsyncGenerator

import pytest

from tests import MyTest


class FakeSchedulerMixin(MyTest):
    @pytest.fixture(autouse=True)
    async def FakeScheduler(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.model import PostIdentifier, Subscription, ScheduleType
        from nonebot_plugin_pixivbot.service.scheduler import Scheduler

        @context.bind_singleton_to(Scheduler)
        class FakeScheduler:
            def __init__(self):
                self.subscriptions = {}
                self.code_gen = 0

            async def schedule(self, type_: ScheduleType,
                               schedule: Union[str, Sequence[int]],
                               args: List[str],
                               post_dest: PostDestination[int, int]):
                from nonebot_plugin_pixivbot.service.scheduler import parse_schedule

                if isinstance(schedule, str):
                    schedule = parse_schedule(schedule)

                kwargs = {}
                for i, arg in enumerate(args):
                    kwargs[str(i)] = arg

                self.code_gen += 1
                code = self.code_gen
                self.subscriptions[code] = Subscription(code=code,
                                                        type=type_,
                                                        schedule=schedule,
                                                        kwargs=kwargs,
                                                        subscriber=post_dest.identifier)

            async def unschedule(self, subscriber: PostIdentifier[int, int], code: int):
                if code in self.subscriptions:
                    del self.subscriptions[code]
                    return True
                else:
                    return False

            async def unschedule_all_by_subscriber(self, subscriber: PostIdentifier[int, int]):
                keys = set()
                for k, v in self.subscriptions.items():
                    if v.subscriber == subscriber:
                        keys.add(k)

                for k in keys:
                    del self.subscriptions[k]

            async def get_by_subscriber(self, subscriber: PostIdentifier[int, int]) \
                    -> AsyncGenerator[Subscription, None]:
                for k, v in self.subscriptions.items():
                    if v.subscriber == subscriber:
                        yield v

        return FakeScheduler

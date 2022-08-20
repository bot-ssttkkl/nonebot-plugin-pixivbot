from typing import Sequence, Optional, List, Union

import pytest

from tests import MyTest


class FakeSchedulerMixin(MyTest):
    @pytest.fixture
    async def fake_scheduler(self, load_pixivbot):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.model import PostIdentifier, Subscription, ScheduleType
        from nonebot_plugin_pixivbot.service.scheduler import Scheduler

        @context.bind_singleton_to(Scheduler)
        class FakeScheduler:
            def __init__(self):
                self.subscriptions = {}

            async def schedule(self, type: ScheduleType,
                               schedule: Union[str, Sequence[int]],
                               args: Optional[list] = None,
                               *, post_dest: PostDestination[int, int]):
                from nonebot_plugin_pixivbot.service.scheduler import parse_schedule

                if isinstance(schedule, str):
                    schedule = parse_schedule(schedule)

                kwargs = {}
                for i, arg in enumerate(args):
                    kwargs[str(i)] = arg

                self.subscriptions[(post_dest.identifier, type)] = Subscription(type=type,
                                                                                schedule=schedule,
                                                                                kwargs=kwargs,
                                                                                subscriber=post_dest.identifier)

            async def unschedule(self, type: ScheduleType,
                                 subscriber: PostIdentifier[int, int]):
                if (subscriber, type) in self.subscriptions:
                    del self.subscriptions[(subscriber, type)]
                    return True
                else:
                    return False

            async def unschedule_all(self, subscriber: PostIdentifier[int, int]):
                keys = list(filter(lambda x: x[0] == subscriber, self.subscriptions.keys()))
                for k in keys:
                    del self.subscriptions[k]

            async def get_by_subscriber(self, subscriber: PostIdentifier[int, int]) -> List[Subscription]:
                keys = list(filter(lambda x: x[0] == subscriber, self.subscriptions.keys()))
                li = []
                for k in keys:
                    li.append(self.subscriptions[k])
                return li

        return FakeScheduler

import pytest

from tests.handler.common import HandlerTester
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_scheduler import FakeSchedulerMixin

schedule_help_text = "\n" \
                     "命令格式：/pixivbot schedule <type> <schedule> [..args]\n" \
                     "参数：\n" \
                     "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
                     "random_user_illust, ranking\n" \
                     "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送）\n" \
                     "  [...args]：根据<type>不同需要提供不同的参数\n" \
                     "示例：/pixivbot schedule ranking 06:00*x day 1-5"


class ScheduleTester(HandlerTester,
                     FakeSchedulerMixin,
                     FakeAuthenticatorManagerMixin,
                     FakePixivAccountBinderMixin):

    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler
        return ScheduleHandler


class TestScheduleHandleNoArgNoSub(ScheduleTester):
    except_msg = "当前订阅：\n" \
                 "无\n" + schedule_help_text


class TestScheduleHandleNoArg(ScheduleTester):
    except_msg = "当前订阅：\n" \
                 "[1] random_bookmark 00:00+00:30*x \n" \
                 "[2] ranking 06:00+00:00*x (0=day)\n" + schedule_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = FakePostDestination(1234, 56789)

        await context.require(FakeScheduler).schedule(type_=ScheduleType.random_bookmark, schedule=(0, 0, 0, 30),
                                                      args=[],
                                                      post_dest=post_dest)
        await context.require(FakeScheduler).schedule(type_=ScheduleType.ranking, schedule=(6, 0, 0, 0), args=["day"],
                                                      post_dest=post_dest)

        await tester(post_dest=post_dest)


class TestScheduleHandleInterval(ScheduleTester):
    args = ["random_bookmark", "00:30*x"]
    except_msg = "订阅成功"

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import ScheduleType, Subscription

        post_dest = FakePostDestination(1234, 56789)

        await tester()

        assert context.require(FakeScheduler).subscriptions[1] == Subscription(
            code=1,
            type=ScheduleType.random_bookmark,
            kwargs={},
            subscriber=post_dest.identifier,
            schedule=(0, 0, 0, 30)
        )


class TestScheduleHandleInvalidArgs(ScheduleTester):
    args = ["invalid_arg_lol", "00:30*x"]
    except_msg = "未知订阅类型：invalid_arg_lol\n" \
                 "当前订阅：\n" \
                 "无\n" + schedule_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler):
        from nonebot_plugin_pixivbot import context

        await tester()

        assert len(context.require(FakeScheduler).subscriptions) == 0


class TestScheduleHandleInvalidArgsCount(ScheduleTester):
    args = ["random_bookmark"]
    except_msg = "当前订阅：\n" \
                 "无\n" + schedule_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler):
        from nonebot_plugin_pixivbot import context

        await tester()

        assert len(context.require(FakeScheduler).subscriptions) == 0

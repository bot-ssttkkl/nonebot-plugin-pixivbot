import pytest

from tests.handler.common import HandlerTester
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_scheduler import FakeSchedulerMixin

unschedule_help_text = "\n" \
                       "命令格式：/pixivbot unschedule <id>"


class UnscheduleTester(HandlerTester,
                       FakeSchedulerMixin,
                       FakeAuthenticatorManagerMixin,
                       FakePixivAccountBinderMixin):

    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler
        return UnscheduleHandler


class TestUnscheduleHandleNoArgNoSub(UnscheduleTester):
    except_msg = "当前订阅：\n" \
                 "无\n" + unschedule_help_text


class TestUnscheduleHandleNoArg(UnscheduleTester):
    except_msg = "当前订阅：\n" \
                 "[1] random_bookmark 00:00+00:30*x\n" \
                 "[2] ranking 06:00+00:00*x\n" + unschedule_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = FakePostDestination(1234, 56789)

        context.require(FakeScheduler).schedule(type_=ScheduleType.random_bookmark, schedule=(0, 0, 0, 30), args=[],
                                                post_dest=post_dest)
        context.require(FakeScheduler).schedule(type_=ScheduleType.ranking, schedule=(6, 0, 0, 0), args=["day"],
                                                post_dest=post_dest)


class TestUnscheduleHandle(UnscheduleTester):
    args = ["1"]
    except_msg = "取消订阅成功"

    @pytest.mark.asyncio
    async def test(self, tester, FakeScheduler, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = FakePostDestination(1234, 56789)

        await context.require(FakeScheduler).schedule(
            type_=ScheduleType.random_bookmark,
            schedule=(0, 0, 0, 30),
            args=[],
            post_dest=post_dest
        )

        await tester()

        assert len(context.require(FakeScheduler).subscriptions) == 0


class TestUnscheduleHandleNotExist(UnscheduleTester):
    args = ["12"]
    except_msg = "取消订阅失败，不存在该订阅\n" \
                 "当前订阅：\n" \
                 "无\n" + unschedule_help_text


class TestUnscheduleHandleInvalidArgs(UnscheduleTester):
    args = ["abce"]
    except_msg = "不合法的订阅编号：abce\n" \
                 "当前订阅：\n" \
                 "无\n" + unschedule_help_text

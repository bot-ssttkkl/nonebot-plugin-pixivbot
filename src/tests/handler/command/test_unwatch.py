import pytest

from tests.handler.common import HandlerTester
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin
from tests.service.fake_watchman import FakeWatchmanMixin

unwatch_help_text = "\n" \
                    "命令格式：/pixivbot unwatch <id>"


class UnwatchTester(HandlerTester,
                    FakeWatchmanMixin,
                    FakeAuthenticatorManagerMixin,
                    FakePixivAccountBinderMixin,
                    FakePixivServiceMixin):

    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler
        return UnwatchHandler


class TestUnwatchHandleNoArgNoSub(UnwatchTester):
    except_msg = "当前订阅：\n" \
                 "无\n" + unwatch_help_text


class TestUnwatchHandleNoArg(UnwatchTester):
    except_msg = "当前订阅：\n" \
                 "[1] user_illusts (user_id=54321)\n" \
                 "[2] following_illusts (sender_user_id=1234)\n" + unwatch_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = FakePostDestination(1234, 56789)

        await context.require(FakeWatchman).watch(type_=WatchType.user_illusts, kwargs={"user_id": 54321},
                                                  subscriber=post_dest)

        await context.require(FakeWatchman).watch(type_=WatchType.following_illusts,
                                                  kwargs={"sender_user_id": 1234, "pixiv_user_id": 0},
                                                  subscriber=post_dest)

        await tester(post_dest=post_dest)


class TestUnscheduleHandle(UnwatchTester):
    args = ["1"]
    except_msg = "取消订阅成功"

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = FakePostDestination(1234, 56789)

        await context.require(FakeWatchman).watch(
            type_=WatchType.user_illusts, kwargs={"user_id": 54321},
            subscriber=post_dest
        )

        await tester()

        assert len(context.require(FakeWatchman).tasks) == 0


class TestUnscheduleHandleNotExist(UnwatchTester):
    args = ["12"]
    except_msg = "取消订阅失败，不存在该订阅\n" \
                 "当前订阅：\n" \
                 "无\n" + unwatch_help_text


class TestUnscheduleHandleInvalidArgs(UnwatchTester):
    args = ["abce"]
    except_msg = "不合法的订阅编号：abce\n" \
                 "当前订阅：\n" \
                 "无\n" + unwatch_help_text

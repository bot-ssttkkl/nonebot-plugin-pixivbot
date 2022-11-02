import pytest

from tests.handler.common import HandlerTester
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin
from tests.service.fake_watchman import FakeWatchmanMixin

watch_help_text = "\n" \
                  "命令格式：/pixivbot watch <type> [..args]\n" \
                  "参数：\n" \
                  "  <type>：可选值有user_illusts, following_illusts\n" \
                  "  [...args]：根据<type>不同需要提供不同的参数\n" \
                  "示例：/pixivbot watch user_illusts <用户名>\n"


class WatchTester(HandlerTester,
                  FakeWatchmanMixin,
                  FakeAuthenticatorManagerMixin,
                  FakePixivAccountBinderMixin,
                  FakePixivServiceMixin):

    @pytest.fixture
    def Handler(self, load_pixivbot):
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        return WatchHandler


class TestWatchHandleNoArgNoSub(WatchTester):
    except_msg = "当前订阅：\n" \
                 "无\n" + watch_help_text


class TestWatchHandleNoArg(WatchTester):
    except_msg = "当前订阅：\n" \
                 "[1] user_illusts (user_id=54321)\n" \
                 "[2] following_illusts (sender_user_id=1234)\n" + watch_help_text

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


class TestWatchHandleUserIllusts(WatchTester):
    args = ["user_illusts", "54321"]
    except_msg = "成功订阅TestUser(54321)老师的插画更新"

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchTask, WatchType

        post_dest = FakePostDestination(1234, 56789)

        await tester(post_dest=post_dest)

        assert context.require(FakeWatchman).tasks[1] == WatchTask(
            code=1,
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest.identifier
        )


class TestWatchHandleUserIllustsByName(WatchTester):
    args = ["user_illusts", "TestUser"]
    except_msg = "成功订阅TestUser(54321)老师的插画更新"

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchTask, WatchType

        post_dest = FakePostDestination(1234, 56789)

        await tester(post_dest=post_dest)

        assert context.require(FakeWatchman).tasks[1] == WatchTask(
            code=1,
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest.identifier
        )


class TestWatchHandleUserIllustsByNameNoData(WatchTester):
    args = ["user_illusts", "NoSuchUser"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        # 因为Watch不是EntryHandler，没有配置异常拦截器
        with pytest.raises(QueryError) as e:
            await tester()


class TestWatchHandleFollowingIllusts(WatchTester):
    args = ["following_illusts", "54321"]
    except_msg = "成功订阅TestUser(54321)用户的关注者插画更新"

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchTask, WatchType

        post_dest = FakePostDestination(1234, 56789)

        await tester(post_dest=post_dest)

        assert context.require(FakeWatchman).tasks[1] == WatchTask(
            code=1,
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 54321, "sender_user_id": 1234},
            subscriber=post_dest.identifier
        )


class TestWatchHandleFollowingIllustsByName(WatchTester):
    args = ["following_illusts", "TestUser"]
    except_msg = "成功订阅TestUser(54321)用户的关注者插画更新"

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman, FakePostDestination):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.model import WatchTask, WatchType

        post_dest = FakePostDestination(1234, 56789)

        await tester(post_dest=post_dest)

        assert context.require(FakeWatchman).tasks[1] == WatchTask(
            code=1,
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 54321, "sender_user_id": 1234},
            subscriber=post_dest.identifier
        )


class TestWatchHandleFollowingIllustsByNameNoData(WatchTester):
    args = ["following_illusts", "NoSuchUser"]

    @pytest.mark.asyncio
    async def test(self, tester, FakePixivService):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        context.require(FakePixivService).no_data = True

        # 因为Watch不是EntryHandler，没有配置异常拦截器
        with pytest.raises(QueryError) as e:
            await tester()


class TestWatchHandleInvalidArgs(WatchTester):
    args = ["invalid_arg_lol"]
    except_msg = "未知订阅类型：invalid_arg_lol\n" \
                 "\n" \
                 "当前订阅：\n" \
                 "无\n" + watch_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman):
        from nonebot_plugin_pixivbot import context

        await tester()

        assert len(context.require(FakeWatchman).tasks) == 0


class TestWatchHandleInvalidArgsCount(WatchTester):
    args = ["user_illusts"]
    except_msg = "当前订阅：\n" \
                 "无\n" + watch_help_text

    @pytest.mark.asyncio
    async def test(self, tester, FakeWatchman):
        from nonebot_plugin_pixivbot import context

        await tester()

        assert len(context.require(FakeWatchman).tasks) == 0

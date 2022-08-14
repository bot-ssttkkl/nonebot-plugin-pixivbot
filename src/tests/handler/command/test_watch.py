import pytest

from tests import MyTest
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_service import FakePixivServiceMixin
from tests.service.fake_watchman import FakeWatchmanMixin


class TestWatchHandler(FakeWatchmanMixin,
                       FakePixivServiceMixin,
                       FakeAuthenticatorManagerMixin,
                       FakePostDestinationMixin,
                       FakePostmanManagerMixin,
                       MyTest):

    @pytest.mark.asyncio
    async def test_handle_no_arg_no_sub(self, fake_post_destination,
                                        fake_postman_manager,
                                        fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot watch <type> <..args>\n" \
                     "示例：/pixivbot watch user_illusts <用户名>\n"

        await context.require(WatchHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_no_arg(self, fake_post_destination,
                                 fake_postman_manager,
                                 fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "user_illusts user_id=54321\n" \
                     "following_illusts sender_user_id=1234 pixiv_user_id=0\n" \
                     "\n" \
                     "命令格式：/pixivbot watch <type> <..args>\n" \
                     "示例：/pixivbot watch user_illusts <用户名>\n"

        await context.require(fake_watchman).watch(
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest
        )

        await context.require(fake_watchman).watch(
            type=WatchType.following_illusts,
            kwargs={"sender_user_id": 1234, "pixiv_user_id": 0},
            subscriber=post_dest
        )

        await context.require(WatchHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_user_illusts(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType, WatchTask

        post_dest = fake_post_destination(1234, 56789)
        except_msg = f"成功订阅TestUser(54321)老师的插画更新"
        except_task = WatchTask(
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest.identifier
        )

        await context.require(WatchHandler).handle("user_illusts", "54321", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert tasks[0] == except_task

    @pytest.mark.asyncio
    async def test_handle_user_illusts_by_name(self, fake_post_destination,
                                               fake_postman_manager,
                                               fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType, WatchTask

        post_dest = fake_post_destination(1234, 56789)
        except_msg = f"成功订阅TestUser(54321)老师的插画更新"
        except_task = WatchTask(
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest.identifier
        )

        await context.require(WatchHandler).handle("user_illusts", "TestUser", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert tasks[0] == except_task

    @pytest.mark.asyncio
    async def test_handle_following_illusts(self, fake_post_destination,
                                            fake_postman_manager,
                                            fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType, WatchTask

        post_dest = fake_post_destination(1234, 56789)
        except_msg = f"成功订阅TestUser(54321)用户的关注者插画更新"
        except_task = WatchTask(
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 54321, "sender_user_id": 1234},
            subscriber=post_dest.identifier
        )

        await context.require(WatchHandler).handle("following_illusts", "54321", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert tasks[0] == except_task

    @pytest.mark.asyncio
    async def test_handle_following_illusts_by_name(self, fake_post_destination,
                                                    fake_postman_manager,
                                                    fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType, WatchTask

        post_dest = fake_post_destination(1234, 56789)
        except_msg = f"成功订阅TestUser(54321)用户的关注者插画更新"
        except_task = WatchTask(
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 54321, "sender_user_id": 1234},
            subscriber=post_dest.identifier
        )

        await context.require(WatchHandler).handle("following_illusts", "TestUser", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert tasks[0] == except_task

    @pytest.mark.asyncio
    async def test_handle_following_illusts_by_bind(self, fake_post_destination,
                                                    fake_postman_manager,
                                                    fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler
        from nonebot_plugin_pixivbot.model import WatchType, WatchTask

        post_dest = fake_post_destination(1234, 56789)
        except_msg = f"成功订阅关注者插画更新"
        except_task = WatchTask(
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 0, "sender_user_id": 1234},
            subscriber=post_dest.identifier
        )

        await context.require(WatchHandler).handle("following_illusts", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert tasks[0] == except_task

    @pytest.mark.asyncio
    async def test_handle_invalid_args(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "未知订阅类型：invalid_arg_lol\n" \
                     "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot watch <type> <..args>\n" \
                     "示例：/pixivbot watch user_illusts <用户名>\n"

        await context.require(WatchHandler).handle("invalid_arg_lol", "00:30*x", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert len(await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)) == 0

    @pytest.mark.asyncio
    async def test_handle_user_illusts_invalid_args_count(self, fake_post_destination,
                                                          fake_postman_manager,
                                                          fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import WatchHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot watch <type> <..args>\n" \
                     "示例：/pixivbot watch user_illusts <用户名>\n"

        await context.require(WatchHandler).handle("user_illusts", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert len(await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)) == 0


class TestUnwatchHandler(FakeWatchmanMixin,
                         FakePixivServiceMixin,
                         FakeAuthenticatorManagerMixin,
                         FakePostDestinationMixin,
                         FakePostmanManagerMixin,
                         MyTest):

    @pytest.mark.asyncio
    async def test_handle_no_arg_no_sub(self, fake_post_destination,
                                        fake_postman_manager,
                                        fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot unwatch <type> <..args>\n" \
                     "示例：/pixivbot unwatch user_illusts <用户名>\n"

        await context.require(UnwatchHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_no_arg(self, fake_post_destination,
                                 fake_postman_manager,
                                 fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "user_illusts user_id=54321\n" \
                     "following_illusts sender_user_id=1234 pixiv_user_id=0\n" \
                     "\n" \
                     "命令格式：/pixivbot unwatch <type> <..args>\n" \
                     "示例：/pixivbot unwatch user_illusts <用户名>\n"

        await context.require(fake_watchman).watch(
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest
        )

        await context.require(fake_watchman).watch(
            type=WatchType.following_illusts,
            kwargs={"sender_user_id": 1234, "pixiv_user_id": 0},
            subscriber=post_dest
        )

        await context.require(UnwatchHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_user_illusts(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "成功取消订阅"

        await context.require(fake_watchman).watch(
            type=WatchType.user_illusts,
            kwargs={"user_id": 54321},
            subscriber=post_dest
        )

        await context.require(UnwatchHandler).handle("user_illusts", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert len(tasks) == 0

    @pytest.mark.asyncio
    async def test_handle_following_illusts(self, fake_post_destination,
                                            fake_postman_manager,
                                            fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler
        from nonebot_plugin_pixivbot.model import WatchType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "成功取消订阅"

        await context.require(fake_watchman).watch(
            type=WatchType.following_illusts,
            kwargs={"pixiv_user_id": 54321, "sender_user_id": 1234},
            subscriber=post_dest
        )

        await context.require(UnwatchHandler).handle("following_illusts", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

        tasks = await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)
        assert len(tasks) == 0

    @pytest.mark.asyncio
    async def test_handle_invalid_args(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_watchman):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.watch import UnwatchHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "未知订阅类型：invalid_arg_lol\n" \
                     "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot unwatch <type> <..args>\n" \
                     "示例：/pixivbot unwatch user_illusts <用户名>\n"

        await context.require(UnwatchHandler).handle("invalid_arg_lol", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert len(await context.require(fake_watchman).get_by_subscriber(post_dest.identifier)) == 0

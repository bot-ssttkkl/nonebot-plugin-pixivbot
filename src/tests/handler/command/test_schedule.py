import pytest

from tests import MyTest
from tests.protocol_dep.fake_auth_manager import FakeAuthenticatorManagerMixin
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin
from tests.service.fake_pixiv_account_binder import FakePixivAccountBinderMixin
from tests.service.fake_scheduler import FakeSchedulerMixin


class TestScheduleHandler(FakeSchedulerMixin,
                          FakeAuthenticatorManagerMixin,
                          FakePostDestinationMixin,
                          FakePostmanManagerMixin,
                          FakePixivAccountBinderMixin,
                          MyTest):
    help_text = "\n" \
                "命令格式：/pixivbot schedule <type> <schedule> [..args]\n" \
                "参数：\n" \
                "  <type>：可选值有random_bookmark, random_recommended_illust, random_illust, " \
                "random_user_illust, ranking\n" \
                "  <schedule>：格式为HH:mm（每日固定时间点推送）或HH:mm*x（间隔时间推送）\n" \
                "  [...args]：根据<type>不同需要提供不同的参数\n" \
                "示例：/pixivbot schedule ranking 06:00*x day 1-5"

    @pytest.mark.asyncio
    async def test_handle_no_arg_no_sub(self, fake_post_destination,
                                        fake_postman_manager,
                                        fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" + self.help_text

        await context.require(ScheduleHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_no_arg(self, fake_post_destination,
                                 fake_postman_manager,
                                 fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler
        from nonebot_plugin_pixivbot.model import Subscription, ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "random_bookmark 00:00+00:30*x\n" \
                     "ranking 06:00+00:00*x\n" + self.help_text

        context.require(fake_scheduler).subscriptions[
            (post_dest.identifier, ScheduleType.random_bookmark)
        ] = Subscription(
            type=ScheduleType.random_bookmark,
            kwargs={},
            subscriber=post_dest.identifier,
            schedule=(0, 0, 0, 30)
        )

        context.require(fake_scheduler).subscriptions[
            (post_dest.identifier, ScheduleType.ranking)
        ] = Subscription(
            type=ScheduleType.ranking,
            kwargs={"type": "day"},
            subscriber=post_dest.identifier,
            schedule=(6, 0, 0, 0)
        )

        await context.require(ScheduleHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_interval_schedule(self, fake_post_destination,
                                            fake_postman_manager,
                                            fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler
        from nonebot_plugin_pixivbot.model import Subscription, ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "订阅成功"
        except_sub = Subscription(
            type=ScheduleType.random_bookmark,
            kwargs={},
            subscriber=post_dest.identifier,
            schedule=(0, 0, 0, 30)
        )

        await context.require(ScheduleHandler).handle("random_bookmark", "00:30*x", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert context.require(fake_scheduler).subscriptions[
                   (post_dest.identifier, ScheduleType.random_bookmark)
               ] == except_sub

    @pytest.mark.asyncio
    async def test_handle_invalid_args(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "未知订阅类型：invalid_arg_lol\n" \
                     "当前订阅：\n" \
                     "无\n" + self.help_text

        await context.require(ScheduleHandler).handle("invalid_arg_lol", "00:30*x", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert (post_dest.identifier, ScheduleType.random_bookmark) not in context.require(fake_scheduler).subscriptions

    @pytest.mark.asyncio
    async def test_handle_invalid_args_count(self, fake_post_destination,
                                             fake_postman_manager,
                                             fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import ScheduleHandler
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" + self.help_text

        await context.require(ScheduleHandler).handle("random_bookmark", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert (post_dest.identifier, ScheduleType.random_bookmark) not in context.require(fake_scheduler).subscriptions


class TestUnscheduleHandler(FakeSchedulerMixin,
                            FakeAuthenticatorManagerMixin,
                            FakePostDestinationMixin,
                            FakePostmanManagerMixin,
                            FakePixivAccountBinderMixin,
                            MyTest):

    @pytest.mark.asyncio
    async def test_handle_no_arg_no_sub(self, fake_post_destination,
                                        fake_postman_manager,
                                        fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot unschedule <type>"

        await context.require(UnscheduleHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle_no_arg(self, fake_post_destination,
                                 fake_postman_manager,
                                 fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler
        from nonebot_plugin_pixivbot.model import Subscription, ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "当前订阅：\n" \
                     "random_bookmark 00:00+00:30*x\n" \
                     "ranking 06:00+00:00*x\n" \
                     "\n" \
                     "命令格式：/pixivbot unschedule <type>"

        context.require(fake_scheduler).subscriptions[
            (post_dest.identifier, ScheduleType.random_bookmark)
        ] = Subscription(
            type=ScheduleType.random_bookmark,
            kwargs={},
            subscriber=post_dest.identifier,
            schedule=(0, 0, 0, 30)
        )

        context.require(fake_scheduler).subscriptions[
            (post_dest.identifier, ScheduleType.ranking)
        ] = Subscription(
            type=ScheduleType.ranking,
            kwargs={"type": "day"},
            subscriber=post_dest.identifier,
            schedule=(6, 0, 0, 0)
        )

        await context.require(UnscheduleHandler).handle(post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)

    @pytest.mark.asyncio
    async def test_handle(self, fake_post_destination,
                          fake_postman_manager,
                          fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler
        from nonebot_plugin_pixivbot.model import Subscription, ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "取消订阅成功"

        context.require(fake_scheduler).subscriptions[
            (post_dest.identifier, ScheduleType.random_bookmark)
        ] = Subscription(
            type=ScheduleType.random_bookmark,
            kwargs={},
            subscriber=post_dest.identifier,
            schedule=(0, 0, 0, 30)
        )

        await context.require(UnscheduleHandler).handle("random_bookmark", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert (post_dest.identifier, ScheduleType.random_bookmark) not in context.require(fake_scheduler).subscriptions

    @pytest.mark.asyncio
    async def test_handle_not_exist(self, fake_post_destination,
                                    fake_postman_manager,
                                    fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "取消订阅失败，不存在该订阅\n" \
                     "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot unschedule <type>"

        await context.require(UnscheduleHandler).handle("random_bookmark", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert (post_dest.identifier, ScheduleType.random_bookmark) not in context.require(fake_scheduler).subscriptions

    @pytest.mark.asyncio
    async def test_handle_invalid_args(self, fake_post_destination,
                                       fake_postman_manager,
                                       fake_scheduler):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.handler.command.schedule import UnscheduleHandler
        from nonebot_plugin_pixivbot.model import ScheduleType

        post_dest = fake_post_destination(1234, 56789)
        except_msg = "未知订阅类型：invalid_arg_lol\n" \
                     "当前订阅：\n" \
                     "无\n" \
                     "\n" \
                     "命令格式：/pixivbot unschedule <type>"

        await context.require(UnscheduleHandler).handle("invalid_arg_lol", post_dest=post_dest)
        assert context.require(fake_postman_manager).calls[0] == (post_dest, except_msg)
        assert (post_dest.identifier, ScheduleType.random_bookmark) not in context.require(fake_scheduler).subscriptions

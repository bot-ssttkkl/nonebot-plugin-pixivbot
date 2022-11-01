from inspect import isawaitable
from typing import List, Union, Optional, Mapping, Any

import pytest

from tests import MyTest
from tests.protocol_dep.fake_post_dest import FakePostDestinationMixin
from tests.protocol_dep.fake_postman import FakePostmanManagerMixin


class HandlerTester(FakePostDestinationMixin,
                    FakePostmanManagerMixin,
                    MyTest):
    args: List[str] = []
    kwargs: Mapping[str, Any] = {}
    except_msg: Union[str, "IllustMessageModel", "IllustMessagesModel"]

    @pytest.fixture(autouse=True)
    def remove_interceptor(self, load_pixivbot, Handler):
        from nonebot_plugin_pixivbot import context

        context.require(Handler).interceptor = None

    @pytest.fixture
    def tester(self, Handler, FakePostDestination, FakePostmanManager):
        async def test(*, except_msg=None, post_dest: Optional[FakePostDestination] = None):
            from nonebot_plugin_pixivbot import context

            if post_dest is None:
                post_dest = FakePostDestination(1234, 56789)

            if except_msg is None:
                except_msg = getattr(self, "except_msg", None)

            await context.require(Handler).handle(*self.args, post_dest=post_dest, **self.kwargs)

            if except_msg is None:
                context.require(FakePostmanManager).assert_not_called(post_dest)
                return

            if callable(except_msg):
                except_msg = except_msg()
                if isawaitable(except_msg):
                    except_msg = await except_msg

            context.require(FakePostmanManager).assert_called(post_dest, except_msg)

        return test

    @pytest.mark.asyncio
    async def test(self, tester):
        await tester()

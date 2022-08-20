from unittest.mock import MagicMock

from tests import MyTest


class TestLazyDelegation(MyTest):
    def test_lazy_delegation(self):
        from nonebot_plugin_pixivbot.utils.lazy_delegation import LazyDelegation

        class A:
            def __init__(self):
                self.hello = "world"
                self.cache = "cache"
                self.builder = "builder"

        builder = MagicMock(return_value=A())
        delegation = LazyDelegation(builder)

        builder.assert_not_called()
        assert delegation.hello == "world"
        builder.assert_called()

        assert delegation.cache == "cache"
        assert delegation.builder == "builder"

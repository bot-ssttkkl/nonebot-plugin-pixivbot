import pytest

from tests import MyTest


class FakeAuthenticatorManagerMixin(MyTest):
    @pytest.fixture(autouse=True)
    def fake_auth_manager(self, load_pixivbot):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
        from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager

        @context.bind_singleton_to(AuthenticatorManager)
        class FakeAuthenticatorManager:
            def group_admin(self, post_dest: PostDestination[int, int]) -> bool:
                return True

        return FakeAuthenticatorManager

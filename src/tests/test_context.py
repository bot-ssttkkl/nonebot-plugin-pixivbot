from unittest.mock import MagicMock

import pytest

from tests import MyTest

cnt = 0


class A:
    def __init__(self, data):
        global cnt
        cnt += 1
        self.data = data

    def hello(self):
        return self.data


class B(A):
    def __init__(self, data):
        super().__init__(data)

    def hello(self):
        return "Hello " + str(self.data)


class TestContext(MyTest):
    @pytest.fixture
    def context(self):
        from nonebot_plugin_pixivbot.context import Context

        context = Context()
        return context

    def test_register_require_contains(self, context):
        context.register(A, A(1))
        assert context.require(A).hello() == 1
        assert A in context

    def test_register_lazy(self, context):
        initializer = MagicMock(side_effect=lambda: A(2))
        context.register_lazy(A, initializer)
        initializer.assert_not_called()
        assert context.require(A).hello() == 2
        initializer.assert_called_once()

    def test_register_singleton(self, context):
        old_cnt = cnt
        context.register_singleton(3)(A)
        assert cnt == old_cnt
        assert context.require(A).hello() == 3
        assert cnt == old_cnt + 1

    def test_register_eager_singleton(self, context):
        old_cnt = cnt
        context.register_eager_singleton(4)(A)
        assert cnt == old_cnt + 1
        assert context.require(A).hello() == 4
        assert cnt == old_cnt + 1

    def test_bind_to(self, context):
        context.register(B, B("world"))
        context.bind(A, B)

        assert context.require(A).hello() == "Hello world"

    def test_bind_instance(self, context):
        @context.bind_singleton_to(B, "world")
        class C(B):
            def __init__(self, data):
                super().__init__(data)

        assert context.require(C).hello() == "Hello world"

    def test_parent(self, context):
        from nonebot_plugin_pixivbot.context import Context
        second = Context(context)
        third = Context(second)

        context.register(A, A(10))
        assert third.require(A).hello() == 10
        assert A in third

    def test_inject(self, context):
        from nonebot_plugin_pixivbot.context import Inject

        context.register(A, A(5))

        @context.inject
        class X:
            a = Inject(A)

        x = X()
        assert x.a.hello() == 5

    def test_inherited_inject(self, context):
        from nonebot_plugin_pixivbot.context import Inject

        context.register(A, A(6))
        context.register(B, A(7))

        @context.inject
        class X:
            a = Inject(A)

        @context.inject
        class Y(X):
            b = Inject(B)

        y = Y()

        assert y.a.hello() == 6
        assert y.b.hello() == 7

import pytest

from nonebug import NONEBOT_INIT_KWARGS


def pytest_configure(config):
    # nonebug 会在 session 级 autouse fixture 中执行 nonebot.init，
    # 这里提前把插件必需配置传给 NoneBot。
    config.stash[NONEBOT_INIT_KWARGS] = {
        "pixiv_refresh_token": "123",
        "superusers": {"test:123456"},
    }


@pytest.fixture(autouse=True)
def conf_env(monkeypatch):
    monkeypatch.setenv("PIXIV_REFRESH_TOKEN", "123")
    monkeypatch.setenv("SUPERUSERS", "[\"test:123456\"]")

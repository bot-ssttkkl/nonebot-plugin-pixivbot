import pytest


@pytest.fixture(autouse=True)
def conf_env(monkeypatch):
    monkeypatch.setenv("PIXIV_REFRESH_TOKEN", "123")
    monkeypatch.setenv("SUPERUSERS", "[\"test:123456\"]")
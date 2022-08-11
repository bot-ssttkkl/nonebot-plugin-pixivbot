import pytest


@pytest.fixture(autouse=True)
def conf_env(monkeypatch):
    monkeypatch.setenv("PIXIV_MONGO_CONN_URL", "123")
    monkeypatch.setenv("PIXIV_MONGO_DATABASE_NAME", "123")
    monkeypatch.setenv("PIXIV_REFRESH_TOKEN", "123")

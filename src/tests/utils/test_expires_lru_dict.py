from asyncio import sleep
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from tests import MyTest


class TestExpiresLruDict(MyTest):
    @pytest.fixture
    def lru(self):
        from nonebot_plugin_pixivbot.utils.expires_lru_dict import AsyncExpiresLruDict

        return AsyncExpiresLruDict(10)

    @pytest.mark.asyncio
    async def test_expires(self, lru):
        lru.on_cleanup = MagicMock()

        expires = datetime.now(timezone.utc) + timedelta(seconds=1)
        lru.add("hello", "world", expires)
        assert lru["hello"] == "world"

        await sleep(2)
        assert "hello" not in lru
        lru.on_cleanup.assert_called_once_with("hello", "world")

        expires = datetime.now(timezone.utc) + timedelta(seconds=30)
        lru.add("hello", "test", expires)
        assert lru["hello"] == "test"

    def test_lru(self, lru):
        lru.on_cleanup = MagicMock()

        expires = datetime.now(timezone.utc) + timedelta(seconds=3)
        for i in range(11):
            lru.add(i, i, expires)

        assert 0 not in lru
        lru.on_cleanup.assert_called_once_with(0, 0)
        for i in range(1, 11):
            assert lru[i] == i

    @pytest.mark.asyncio
    async def test_expires_lru(self, lru):
        now = datetime.now(timezone.utc)
        for i in range(5):
            lru.add(i, i, now + timedelta(seconds=2))
        for i in range(5, 10):
            lru.add(i, i, now + timedelta(seconds=20))
        # except: 0 1 2 3 4 5 6 7 8 9

        await sleep(3)
        for i in range(5):
            assert i not in lru
        for i in range(5, 10):
            assert lru[i] == i
        # except: 5 6 7 8 9

        now = datetime.now(timezone.utc)
        for i in range(10, 18):
            lru.add(i, i, now + timedelta(seconds=20))
        # except: 8 9 10 11 12 13 14 15 16 17

        for i in range(5, 8):
            assert i not in lru
        for i in range(8, 18):
            assert lru[i] == i

    @pytest.mark.asyncio
    async def test_set(self, lru):
        now = datetime.now(timezone.utc)

        lru.add("hello", "world", now + timedelta(seconds=1))
        assert lru["hello"] == "world"

        lru["hello"] = "python"
        assert lru["hello"] == "python"

    def test_add_key_error(self, lru):
        now = datetime.now(timezone.utc)
        lru.add("test", "py", now + timedelta(seconds=1))
        with pytest.raises(KeyError):
            lru.add("test", "pyyy", now + timedelta(seconds=1))

    def test_set_key_error(self, lru):
        with pytest.raises(KeyError):
            lru["test"] = "py"

    @pytest.mark.asyncio
    async def test_del(self, lru):
        now = datetime.now(timezone.utc)

        lru.add("hello", "world", now + timedelta(seconds=1))
        del lru["hello"]
        assert "hello" not in lru

        lru.add("hello", "python", now + timedelta(seconds=30))
        await sleep(1.5)
        assert lru["hello"] == "python"

    @pytest.mark.asyncio
    async def test_del2(self, lru):
        now = datetime.now(timezone.utc)

        lru.add("hello", "world", now + timedelta(seconds=1))
        del lru["hello"]
        assert "hello" not in lru

        lru.add("hello", "python", now + timedelta(seconds=1))
        assert lru["hello"] == "python"

        await sleep(1.5)
        assert "hello" not in lru

    @pytest.mark.asyncio
    async def test_collate_expires_heap(self, lru):
        now = datetime.now(timezone.utc)
        for i in range(1, 21):
            lru.add(i, i, now + timedelta(milliseconds=100 * i))
            print(len(lru._expires_heap))

        await sleep(3)

        now = datetime.now(timezone.utc)
        lru.add("hello", "world", now + timedelta(seconds=20))

        for i in range(1, 21):
            assert i not in lru

        assert lru["hello"] == "world"

from asyncio import sleep
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from tests import MyTest


class TestExpiresLruDict(MyTest):
    @pytest.fixture
    def lru(self):
        from nonebot_plugin_pixivbot.utils.expires_lru_dict import AsyncExpiresLruDict

        lru = AsyncExpiresLruDict(10)
        lru.on_cleanup = MagicMock()

        async def side_effect(*args, **kwargs):
            pass

        lru.on_cleanup.side_effect = side_effect
        return lru

    @pytest.mark.asyncio
    async def test_expires(self, lru):
        expires = datetime.now(timezone.utc) + timedelta(seconds=1)
        await lru.add("hello", "world", expires)
        assert await lru.get("hello") == "world"

        await sleep(2)
        assert await lru.get("hello") is None
        lru.on_cleanup.assert_called_once_with("hello", "world")

        expires = datetime.now(timezone.utc) + timedelta(seconds=30)
        await lru.add("hello", "test", expires)
        assert await lru.get("hello") == "test"

    @pytest.mark.asyncio
    async def test_lru(self, lru):
        expires = datetime.now(timezone.utc) + timedelta(seconds=3)
        for i in range(11):
            await lru.add(i, i, expires)

        assert await lru.get(0) is None
        lru.on_cleanup.assert_called_once_with(0, 0)
        for i in range(1, 11):
            assert await lru.get(i) == i

    @pytest.mark.asyncio
    async def test_expires_lru(self, lru):
        now = datetime.now(timezone.utc)
        for i in range(5):
            await lru.add(i, i, now + timedelta(seconds=2))
        for i in range(5, 10):
            await lru.add(i, i, now + timedelta(seconds=20))
        # except: 0 1 2 3 4 5 6 7 8 9

        await sleep(3)
        for i in range(5):
            assert await lru.get(i) is None
        for i in range(5, 10):
            assert await lru.get(i) == i
        # except: 5 6 7 8 9

        now = datetime.now(timezone.utc)
        for i in range(10, 18):
            await lru.add(i, i, now + timedelta(seconds=20))
        # except: 8 9 10 11 12 13 14 15 16 17

        for i in range(5, 8):
            assert await lru.get(i) is None
        for i in range(8, 18):
            assert await lru.get(i) == i

    @pytest.mark.asyncio
    async def test_set(self, lru):
        now = datetime.now(timezone.utc)

        await lru.add("hello", "world", now + timedelta(seconds=1))
        assert await lru.get("hello") == "world"

        await lru.set("hello", "python")
        assert await lru.get("hello") == "python"

    @pytest.mark.asyncio
    async def test_add_key_error(self, lru):
        now = datetime.now(timezone.utc)
        await lru.add("test", "py", now + timedelta(seconds=1))
        with pytest.raises(KeyError):
            await lru.add("test", "pyyy", now + timedelta(seconds=1))

    @pytest.mark.asyncio
    async def test_set_key_error(self, lru):
        with pytest.raises(KeyError):
            await lru.set("test", "py")

    @pytest.mark.asyncio
    async def test_del(self, lru):
        now = datetime.now(timezone.utc)

        await lru.add("hello", "world", now + timedelta(seconds=1))
        await lru.pop("hello")
        assert await lru.get("hello") is None

        await lru.add("hello", "python", now + timedelta(seconds=30))
        await sleep(1.5)
        assert await lru.get("hello") == "python"

    @pytest.mark.asyncio
    async def test_del2(self, lru):
        now = datetime.now(timezone.utc)

        await lru.add("hello", "world", now + timedelta(seconds=1))
        await lru.pop("hello")
        assert await lru.get("hello") is None

        await lru.add("hello", "python", now + timedelta(seconds=1))
        assert await lru.get("hello") == "python"

        await sleep(1.5)
        assert await lru.get("hello") is None

    @pytest.mark.asyncio
    async def test_collate_expires_heap(self, lru):
        now = datetime.now(timezone.utc)
        for i in range(1, 21):
            await lru.add(i, i, now + timedelta(milliseconds=100 * i))
            print(len(lru._expires_heap))

        await sleep(3)

        now = datetime.now(timezone.utc)
        await lru.add("hello", "world", now + timedelta(seconds=20))

        for i in range(1, 21):
            assert await lru.get(i) is None

        assert await lru.get("hello") == "world"

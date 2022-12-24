from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest

from tests import MyTest


class FakePixivRepoMixin(MyTest):
    @pytest.fixture
    def FakePixivRepo(self, load_pixivbot):
        from nonebot_plugin_pixivbot.global_context import context
        from nonebot_plugin_pixivbot.data.pixiv_repo import LazyIllust
        from nonebot_plugin_pixivbot.data.pixiv_repo.base import PixivRepo
        from nonebot_plugin_pixivbot.enums import RankingMode
        from nonebot_plugin_pixivbot.model import Illust, User

        @context.bind_singleton_to(PixivRepo)
        class FakePixivRepo(PixivRepo):
            invalidate_cache = AsyncMock()

            def illust_detail(self, illust_id: int) -> AsyncGenerator[Illust, None]:
                pass

            def user_detail(self, user_id: int) -> AsyncGenerator[User, None]:
                pass

            def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
                pass

            def search_user(self, word: str) -> AsyncGenerator[User, None]:
                pass

            def user_illusts(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
                pass

            def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
                pass

            def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
                pass

            def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
                pass

            def illust_ranking(self, mode: RankingMode) -> AsyncGenerator[LazyIllust, None]:
                pass

            def image(self, illust: Illust) -> AsyncGenerator[bytes, None]:
                pass

        return FakePixivRepo

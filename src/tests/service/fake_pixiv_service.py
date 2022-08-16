import importlib.resources as pkg_resources
import json
from typing import Union, List, Tuple

import pytest

from tests import MyTest


class FakePixivServiceMixin(MyTest):
    @pytest.fixture
    def sample_illusts(self):
        from nonebot_plugin_pixivbot.model import Illust

        from . import resources
        with pkg_resources.open_text(resources, 'sample_illusts.json') as f:
            obj = json.load(f)

        samples = []
        for x in obj:
            samples.append(Illust.parse_obj(x))

        return samples

    @pytest.fixture(autouse=True)
    def fake_pixiv_service(self, load_pixivbot, sample_illusts):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.enums import RankingMode
        from nonebot_plugin_pixivbot.model import User, Illust
        from nonebot_plugin_pixivbot.service.pixiv_service import PixivService

        @context.bind_singleton_to(PixivService)
        class FakePixivService:
            def get_sample(self, num: int) -> Illust:
                return sample_illusts[num]

            async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[Illust]:
                count = range[1] - range[0] + 1
                return sample_illusts[:count]

            async def illust_detail(self, illust: int) -> Illust:
                return sample_illusts[0].copy(update={"id": illust})

            async def random_illust(self, word: str, *, count: int = 1) -> List[Illust]:
                return sample_illusts[:count]

            async def get_user(self, user: Union[str, int]) -> User:
                if isinstance(user, str):
                    return User(id=54321, name=user, account=user)
                else:
                    return User(id=user, name="TestUser", account="test_user")

            async def random_user_illust(self, user: Union[str, int], *, count: int = 1) -> Tuple[User, List[Illust]]:
                return sample_illusts[:count]

            async def random_recommended_illust(self, *, count: int = 1) -> List[Illust]:
                return sample_illusts[:count]

            async def random_bookmark(self, pixiv_user_id: int = 0, *, count: int = 1) -> List[Illust]:
                return sample_illusts[:count]

            async def random_related_illust(self, illust_id: int, *, count: int = 1) -> List[Illust]:
                return sample_illusts[:count]

        return FakePixivService

import importlib.resources as pkg_resources
import json
import random
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
    def FakePixivService(self, load_pixivbot, sample_illusts, mocker):
        from nonebot_plugin_pixivbot import context
        from nonebot_plugin_pixivbot.enums import RankingMode
        from nonebot_plugin_pixivbot.model import User, Illust
        from nonebot_plugin_pixivbot.service.pixiv_service import PixivService
        from nonebot_plugin_pixivbot.utils.errors import QueryError

        @context.bind_singleton_to(PixivService)
        class FakePixivService:
            def __init__(self):
                self.no_data = False

                self.spy_illust_ranking = mocker.spy(self, "illust_ranking")
                self.spy_illust_detail = mocker.spy(self, "illust_detail")
                self.spy_random_illust = mocker.spy(self, "random_illust")
                self.spy_get_user = mocker.spy(self, "get_user")
                self.spy_random_user_illust = mocker.spy(self, "random_user_illust")
                self.spy_random_recommended_illust = mocker.spy(self, "random_recommended_illust")
                self.spy_random_bookmark = mocker.spy(self, "random_bookmark")
                self.spy_random_related_illust = mocker.spy(self, "random_related_illust")

            async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[Illust]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    count = range[1] - range[0] + 1
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return ans

            async def illust_detail(self, illust: int) -> Illust:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[0].copy(update={"id": illust})
                    return ans

            async def random_illust(self, word: str, *, count: int = 1) -> List[Illust]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return ans

            async def get_user(self, user: Union[str, int]) -> User:
                if user == "TestUser" or user == 54321:
                    return User(id=54321, name="TestUser", account=user)
                else:
                    raise QueryError("总之是Pixiv返回的错误信息")

            async def random_user_illust(self, user: Union[str, int], *, count: int = 1) -> Tuple[User, List[Illust]]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return await self.get_user(user), ans

            async def random_recommended_illust(self, *, count: int = 1) -> List[Illust]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return ans

            async def random_bookmark(self, pixiv_user_id: int = 0, *, count: int = 1) -> List[Illust]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return ans

            async def random_related_illust(self, illust_id: int, *, count: int = 1) -> List[Illust]:
                if self.no_data:
                    raise QueryError("总之是Pixiv返回的错误信息")
                else:
                    random.shuffle(sample_illusts)
                    ans = sample_illusts[:count]
                    return ans

        return FakePixivService

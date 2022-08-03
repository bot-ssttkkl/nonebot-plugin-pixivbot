import asyncio
from typing import List, Union, Tuple

from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.local_tag_repo import LocalTagRepo
from nonebot_plugin_pixivbot.data.pixiv_repo import LazyIllust, PixivRepo
from nonebot_plugin_pixivbot.enums import RandomIllustMethod, RankingMode
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Illust, User
from nonebot_plugin_pixivbot.service.roulette import roulette
from nonebot_plugin_pixivbot.utils.errors import BadRequestError, QueryError


@context.inject
@context.register_singleton()
class PixivService:
    conf: Config
    repo: PixivRepo
    local_tags: LocalTagRepo

    async def _choice_and_load(self, illusts: List[LazyIllust], random_method: RandomIllustMethod, count: int) \
            -> List[Illust]:
        if count <= 0:
            raise BadRequestError("不合法的请求数量")
        if count > self.conf.pixiv_max_item_per_query:
            raise BadRequestError("数量超过单次请求上限")
        if count > len(illusts):
            raise QueryError("别看了，没有的。")

        winners = roulette(illusts, random_method, count)
        logger.info(f"choice {[x.id for x in winners]}")
        return [await x.get() for x in winners]

    async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[Illust]:
        illusts = await self.repo.illust_ranking(mode, range)
        return [await x.get() for x in illusts]

    async def illust_detail(self, illust: int) -> Illust:
        return await self.repo.illust_detail(illust)

    async def random_illust(self, word: str, *, count: int = 1) -> List[Illust]:
        if self.conf.pixiv_tag_translation_enabled:
            # 只有原word不是标签时获取翻译（例子：唐可可）
            tag = await self.local_tags.get_by_name(word)
            if not tag:
                tag = await self.local_tags.get_by_translated_name(word)
                if tag:
                    logger.info(f"found translation {word} -> {tag.name}")
                    word = tag.name

        illusts = [x async for x in self.repo.search_illust(word)]
        return await self._choice_and_load(illusts, self.conf.pixiv_random_illust_method, count)

    async def get_user(self, user: Union[str, int]) -> User:
        if isinstance(user, str):
            async for x in self.repo.search_user(user):
                return x
            raise QueryError("未找到用户")
        else:
            return await self.repo.user_detail(user)

    async def random_user_illust(self, user: Union[str, int], *, count: int = 1) -> Tuple[User, List[Illust]]:
        user = await self.get_user(user)
        illusts = [x async for x in self.repo.user_illusts(user.id)]
        illust = await self._choice_and_load(illusts, self.conf.pixiv_random_user_illust_method, count)
        return user, illust

    async def random_recommended_illust(self, *, count: int = 1) -> List[Illust]:
        illusts = [x async for x in self.repo.recommended_illusts()]
        return await self._choice_and_load(illusts, self.conf.pixiv_random_recommended_illust_method, count)

    async def random_bookmark(self, pixiv_user_id: int = 0, *, count: int = 1) -> List[Illust]:
        illusts = [x async for x in self.repo.user_bookmarks(pixiv_user_id)]
        return await self._choice_and_load(illusts, self.conf.pixiv_random_bookmark_method, count)

    async def random_related_illust(self, illust_id: int, *, count: int = 1) -> List[Illust]:
        if illust_id == 0:
            raise BadRequestError("你还没有发送过请求")

        illusts = [x async for x in self.repo.related_illusts(illust_id)]
        return await self._choice_and_load(illusts, self.conf.pixiv_random_related_illust_method, count)


__all__ = ("PixivService",)

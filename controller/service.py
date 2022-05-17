import math
import random
import time
import typing

from nonebot import logger

from ..config import Config
from ..data_source import PixivBindings, PixivDataSource, LazyIllust, LocalTags
from ..model import Illust, User
from ..errors import BadRequestError, QueryError
from .pkg_context import context
from .roulette import roulette


@context.export_singleton()
class Service:
    conf = context.require(Config)
    data_source = context.require(PixivDataSource)
    pixiv_bindings = context.require(PixivBindings)
    local_tags = context.require(LocalTags)

    async def _choice_and_load(self, illusts: typing.List[LazyIllust], random_method: str, count: int) -> typing.List[Illust]:
        if count <= 0:
            raise BadRequestError("不合法的请求数量")
        if count > self.conf.pixiv_max_item_per_query:
            raise BadRequestError("数量超过单次请求上限")
        if count > len(illusts):
            raise QueryError("别看了，没有的。")

        winners = roulette(illusts, random_method, count)
        logger.info(f"choice {[x.id for x in winners]}")
        return [await x.get() for x in winners]

    async def illust_ranking(self, mode: str,
                             range: typing.Sequence[int]) -> typing.List[Illust]:
        start, end = range
        illusts = await self.data_source.illust_ranking(mode, skip=start-1, limit=end-start+1)

        return [await x.get() for x in illusts]

    async def illust_detail(self, illust: int) -> Illust:
        return await self.data_source.illust_detail(illust)

    async def random_illust(self, word: str, *, count: int = 1) -> typing.List[Illust]:
        if self.conf.pixiv_tag_translation_enabled:
            tag = await self.local_tags.get_by_translated_name(word)
            if tag:
                logger.info(f"found translation {word} -> {tag.name}")
                word = tag.name

        illusts = await self.data_source.search_illust(word)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_illust_method, count)

    async def get_user(self, user: typing.Union[str, int]) -> User:
        if isinstance(user, str):
            users = await self.data_source.search_user(user)
            if len(users) == 0:
                raise QueryError("未找到用户")
            else:
                return users[0]
        else:
            return await self.data_source.user_detail(user)

    async def random_user_illust(self, user: typing.Union[str, int], *, count: int = 1) -> typing.Tuple[User, typing.List[Illust]]:
        user = await self.get_user(user)
        illusts = await self.data_source.user_illusts(user.id)
        illust = await self._choice_and_load(illusts, self.conf.pixiv_random_user_illust_method, count)
        return user, illust

    async def random_recommended_illust(self, *, count: int = 1) -> typing.List[Illust]:
        illusts = await self.data_source.recommended_illusts()
        return await self._choice_and_load(illusts, self.conf.pixiv_random_recommended_illust_method, count)

    async def random_bookmark(self, sender_user_id: int = 0, pixiv_user_id: int = 0, *, count: int = 1) -> typing.List[Illust]:
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await self.pixiv_bindings.get_binding(sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        illusts = await self.data_source.user_bookmarks(pixiv_user_id)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_bookmark_method, count)

    async def random_related_illust(self, illust_id: int, *, count: int = 1) -> typing.List[Illust]:
        if illust_id == 0:
            raise BadRequestError("你还没有发送过请求")

        illusts = await self.data_source.related_illusts(illust_id)
        return await self._choice_and_load(illusts, self.conf.pixiv_random_related_illust_method, count)

from typing import AsyncGenerator

from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.model import UserPreview, Illust
from nonebot_plugin_pixivbot.service.watchman.pkg_context import context


async def user_illusts(user_preview: UserPreview) -> AsyncGenerator[Illust, None]:
    if len(user_preview.illusts) < 3:
        for illust in user_preview.illusts:
            yield illust
    else:
        for illust in user_preview.illusts:
            yield illust

        gen = context.require(PixivRepo).user_illusts(user_preview.user.id, CacheStrategy.FORCE_EXPIRATION)

        for i in range(len(user_preview.illusts)):
            await gen.__anext__()

        async for x in gen:
            yield await x.get()


async def user_following_illusts(user_id: int) -> AsyncGenerator[Illust, None]:
    n = 0
    gen = []
    peeked = []

    async for user_preview in context.require(PixivRepo).user_following_with_preview(user_id):
        n += 1
        gen.append(user_illusts(user_preview))
        peeked.append(None)

    try:
        while True:
            select = -1
            for i in range(n):
                try:
                    if not peeked[i]:
                        peeked[i] = await gen[i].__anext__()

                    if select == -1 or peeked[i].create_date > peeked[select].create_date:
                        select = i
                except StopAsyncIteration:
                    pass

            if select == -1:
                break

            yield peeked[select]
            peeked[select] = None
    except GeneratorExit:
        for gen in gen:
            await gen.aclose()

import time

from nonebot import logger

from .base import WatchTaskHandler
from ..pkg_context import context
from ...data.pixiv_repo import PixivRepo
from ...data.pixiv_repo.enums import CacheStrategy
from ...data.pixiv_repo.remote_repo import RemotePixivRepo
from ...model import WatchTask, Illust
from ...utils.shared_agen import SharedAsyncGeneratorManager

pixiv = context.require(PixivRepo)
remote_pixiv = context.require(RemotePixivRepo)


# 因为要强制从远端获取，所以用这个shared_agen_mgr来缓存
class WatchUserIllustsSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[int, Illust]):
    log_tag = "watch_user_illusts_shared_agen"

    async def agen(self, identifier: int, cache_strategy: CacheStrategy, **kwargs):
        await self.set_expires_time(identifier, time.time() + 30)  # 30s过期，保证每分钟的所有task都能共享
        async for x in pixiv.user_illusts(user_id=identifier,
                                          cache_strategy=CacheStrategy.FORCE_EXPIRATION):
            yield await x.get()


shared_agen_mgr = WatchUserIllustsSharedAsyncGeneratorManager()


class WatchUserIllustsHandler(WatchTaskHandler):
    @classmethod
    def type(cls) -> str:
        return "watch_user_illusts"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, task: WatchTask):
        async with shared_agen_mgr.get(task.kwargs["user_id"]) as illusts:
            async for illust in illusts:
                if illust.create_date <= task.checkpoint:
                    break
                logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                await self.post_illust(illust, header="您订阅的画师更新了")

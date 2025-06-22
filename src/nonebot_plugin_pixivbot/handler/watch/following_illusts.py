import time

from nonebot import logger
from datetime import datetime, timedelta, timezone

from .base import WatchTaskHandler
from ..pkg_context import context
from ...config import Config
from ...data.pixiv_repo import PixivRepo
from ...data.pixiv_repo.enums import CacheStrategy
from ...model import WatchTask, Illust
from ...service.pixiv_account_binder import PixivAccountBinder
from ...utils.shared_agen import SharedAsyncGeneratorManager
from ...data.watch_task import WatchTaskRepo

conf = context.require(Config)
binder = context.require(PixivAccountBinder)
pixiv = context.require(PixivRepo)


# 因为要强制从远端获取，所以用这个shared_agen_mgr来缓存
class WatchFollowingIllustsSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[int, Illust]):
    log_tag = "watch_following_illusts_shared_agen"

    async def agen(self, identifier: int, cache_strategy: CacheStrategy, **kwargs):
        await self.set_expires_time(identifier, time.time() + 30)  # 30s过期，保证每分钟的所有task都能共享
        async for x in pixiv.user_following_illusts(user_id=identifier,
                                                    cache_strategy=CacheStrategy.FORCE_EXPIRATION):
            yield await x.get()


shared_agen_mgr = WatchFollowingIllustsSharedAsyncGeneratorManager()


class WatchFollowingIllustsHandler(WatchTaskHandler):
    @classmethod
    def type(cls) -> str:
        return "watch_user_illusts"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, task: WatchTask):
        pixiv_user_id = task.kwargs.get("pixiv_user_id", 0)
        sender_user_id = task.kwargs.get("sender_user_id", 0)

        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(task.subscriber.platform, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            logger.warning(f"[watchman] no binding found for {task.subscriber.id1}")
            return

        async with shared_agen_mgr.get(pixiv_user_id) as illusts:
            get_illust_count = 0  # 初始化已获取的作品数量
            new_illusts = []  # 存储待发送作品到列表
            async for illust in illusts:
                if illust.create_date <= task.checkpoint:
                    break
                new_illusts.append(illust)  # 将作品存入待发送列表
                get_illust_count += 1
                # 只获取x个作品就退出, 避免Rate Limit
                if get_illust_count >= conf.pixiv_watch_fetch_count:
                    break
            if new_illusts:
                # 按时间正序(从旧到新)发送作品
                for illust in reversed(new_illusts):
                    logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                    await self.post_illust(illust, header="您关注的画师更新了")
                # 所有作品发送完后再将任务的checkpoint设为最新作品的时间
                task.checkpoint = new_illusts[0].create_date
                await WatchTaskRepo.update(self, task)

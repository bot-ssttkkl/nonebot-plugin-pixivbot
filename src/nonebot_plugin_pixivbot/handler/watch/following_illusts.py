import time

from nonebot import logger

from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.handler.watch.base import WatchTaskHandler
from nonebot_plugin_pixivbot.model import WatchTask, Illust
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from ..pkg_context import context
from ...config import Config

conf = context.require(Config)
binder = context.require(PixivAccountBinder)
pixiv = context.require(PixivRepo)


# 因为要强制从远端获取，所以用这个shared_agen_mgr来缓存
@context.register_singleton()
class WatchFollowingIllustsSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[int, Illust]):
    log_tag = "watch_following_illusts_shared_agen"

    async def agen(self, identifier: int, cache_strategy: CacheStrategy, **kwargs):
        await self.set_expires_time(identifier, time.time() + 30)  # 30s过期，保证每分钟的所有task都能共享
        async for x in pixiv.user_following_illusts(user_id=identifier,
                                                    cache_strategy=CacheStrategy.FORCE_EXPIRATION):
            yield await x.get()


shared_agen_mgr = context.require(WatchFollowingIllustsSharedAsyncGeneratorManager)


class WatchFollowingIllustsHandler(WatchTaskHandler):
    @classmethod
    def type(cls) -> str:
        return "watch_user_illusts"

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, task: WatchTask):
        pixiv_user_id = task.kwargs.get("pixiv_user_id", 0)
        sender_user_id = task.kwargs.get("sender_user_id", 0)

        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(self.post_dest.adapter, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            logger.warning(f"[watchman] no binding found for {self.post_dest}")
            return

        async with shared_agen_mgr.get(pixiv_user_id) as illusts:
            async for illust in illusts:
                if illust.create_date <= task.checkpoint:
                    break
                logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                await self.post_illust(illust, header="您关注的画师更新了")

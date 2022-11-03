from datetime import datetime, timedelta, timezone

from nonebot import logger

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.data.pixiv_repo.remote_repo import RemotePixivRepo
from nonebot_plugin_pixivbot.handler.watch.base import WatchTaskHandler
from nonebot_plugin_pixivbot.model import WatchTask, Illust, T_GID, T_UID
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from ..pkg_context import context
# 因为要强制从远端获取，所以用这个shared_agen_mgr来缓存
from ...protocol_dep.post_dest import PostDestination


@context.inject
@context.register_singleton()
class WatchFollowingIllustsSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[int, Illust]):
    log_tag = "watch_following_illusts_shared_agen"

    pixiv = Inject(PixivRepo)
    remote_pixiv = Inject(RemotePixivRepo)

    async def agen(self, identifier: int, cache_strategy: CacheStrategy, **kwargs):
        self.set_expires_time(identifier, datetime.now(timezone.utc) + timedelta(seconds=30))  # 保证每分钟的所有task都能共享
        async for x in self.pixiv.user_following_illusts(user_id=identifier,
                                                         cache_strategy=CacheStrategy.FORCE_EXPIRATION):
            yield await x.get()


@context.inject
@context.root.register_singleton()
class WatchFollowingIllustsHandler(WatchTaskHandler):
    shared_agen_mgr = Inject(WatchFollowingIllustsSharedAsyncGeneratorManager)
    binder = Inject(PixivAccountBinder)

    @classmethod
    def type(cls) -> str:
        return "watch_user_illusts"

    def enabled(self) -> bool:
        return True

    # noinspection PyMethodOverriding
    async def actual_handle(self, *, task: WatchTask,
                            post_dest: PostDestination[T_UID, T_GID],
                            silently: bool = False,
                            **kwargs):
        pixiv_user_id = task.kwargs.get("pixiv_user_id", 0)
        sender_user_id = task.kwargs.get("sender_user_id", 0)

        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await self.binder.get_binding(post_dest.adapter, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            logger.warning(f"[watchman] no binding found for {post_dest}")
            return

        with self.shared_agen_mgr.get(pixiv_user_id) as illusts:
            async for illust in illusts:
                if illust.create_date <= task.checkpoint:
                    break
                logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                await self.post_illust(illust, header="您关注的画师更新了", post_dest=post_dest)

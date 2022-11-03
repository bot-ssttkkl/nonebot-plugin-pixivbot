from datetime import datetime, timedelta, timezone

from nonebot import logger

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.data.pixiv_repo.remote_repo import RemotePixivRepo
from nonebot_plugin_pixivbot.model import WatchTask, Illust, T_UID, T_GID
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from .base import WatchTaskHandler
from ..pkg_context import context
# 因为要强制从远端获取，所以用这个shared_agen_mgr来缓存
from ...protocol_dep.post_dest import PostDestination


@context.inject
@context.register_singleton()
class WatchUserIllustsSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[int, Illust]):
    log_tag = "watch_user_illusts_shared_agen"

    pixiv = Inject(PixivRepo)
    remote_pixiv = Inject(RemotePixivRepo)

    async def agen(self, identifier: int, cache_strategy: CacheStrategy, **kwargs):
        self.set_expires_time(identifier, datetime.now(timezone.utc) + timedelta(seconds=30))  # 保证每分钟的所有task都能共享
        async for x in self.pixiv.user_illusts(user_id=identifier,
                                               cache_strategy=CacheStrategy.FORCE_EXPIRATION):
            yield await x.get()


@context.inject
@context.root.register_singleton()
class WatchUserIllustsHandler(WatchTaskHandler):
    shared_agen_mgr = Inject(WatchUserIllustsSharedAsyncGeneratorManager)

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
        with self.shared_agen_mgr.get(task.kwargs["user_id"]) as illusts:
            async for illust in illusts:
                if illust.create_date <= task.checkpoint:
                    break
                logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                await self.post_illust(illust, header="您订阅的画师更新了", post_dest=post_dest)

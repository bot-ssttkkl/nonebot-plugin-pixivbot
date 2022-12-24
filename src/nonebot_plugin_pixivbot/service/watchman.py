from datetime import datetime, timedelta, timezone
from typing import Dict, Any, overload

from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.watch_task import WatchTaskRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.watch.following_illusts import WatchFollowingIllustsHandler
from nonebot_plugin_pixivbot.handler.watch.user_illusts import WatchUserIllustsHandler
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model import WatchTask, WatchType
from nonebot_plugin_pixivbot.plugin_service import receive_watch_service
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from nonebot_plugin_pixivbot.service.interval_task_worker import IntervalTaskWorker
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.nonebot import get_bot_user_identifier


@context.root.register_eager_singleton()
@context.inject
class Watchman(IntervalTaskWorker[WatchTask[T_UID, T_GID]]):
    tag = "watchman"
    repo_type = WatchTaskRepo

    conf = Inject(Config)
    binder = Inject(PixivAccountBinder)
    postman_mgr = Inject(PostmanManager)
    repo: WatchTaskRepo = Inject(WatchTaskRepo)

    _trigger_hasher_mapper = {
        WatchType.user_illusts: lambda args: args["user_id"],
        WatchType.following_illusts: lambda args: hash(args["sender_user_id"]),
    }

    _handlers = {
        WatchType.user_illusts: context.require(WatchUserIllustsHandler),
        WatchType.following_illusts: context.require(WatchFollowingIllustsHandler),
    }

    async def _handle_trigger(self, task: WatchTask[T_UID, T_GID], post_dest: PostDestination[T_UID, T_GID],
                              manually: bool = False):
        if await receive_watch_service.get_permission(*post_dest.extract_subjects()):
            try:
                await self._handlers[task.type].handle_with_parsed_args(post_dest=post_dest, silently=not manually,
                                                                        task=task, disabled_interceptors=manually)
            finally:
                # 保存checkpoint，避免一次异常后下一次重复推送
                # 但是会存在丢失推送的问题
                task.checkpoint = datetime.now(timezone.utc)
                await self.repo.update(task)
        else:
            logger.info(f"[{self.tag}] job cancelled")

    def _make_job_trigger(self, item: WatchTask[T_UID, T_GID]) -> IntervalTrigger:
        hasher = self._trigger_hasher_mapper[item.type]
        hash_sec = hasher(item.kwargs) % self.conf.pixiv_watch_interval
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=-1) + timedelta(seconds=hash_sec)
        trigger = IntervalTrigger(seconds=self.conf.pixiv_watch_interval, start_date=yesterday)
        return trigger

    async def _build_task(self, type_: WatchType,
                          kwargs: Dict[str, Any],
                          post_dest: PostDestination[T_UID, T_GID]) -> WatchTask:
        return WatchTask(type=type_, kwargs=kwargs,
                         subscriber=post_dest.identifier,
                         bot=get_bot_user_identifier(post_dest.bot))

    @overload
    async def add_task(self, type_: WatchType,
                       kwargs: Dict[str, Any],
                       post_dest: PostDestination[T_UID, T_GID]) -> bool:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        return await super().add_task(*args, **kwargs)

    async def fetch(self, code: str, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        task = await self.repo.get_by_code(get_bot_user_identifier(post_dest.bot),
                                           post_dest.identifier, code)
        if task is not None:
            await self._handle_trigger(task, post_dest, manually=True)
            return True
        return False

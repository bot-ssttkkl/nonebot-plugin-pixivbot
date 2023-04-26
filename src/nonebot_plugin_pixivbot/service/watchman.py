from datetime import datetime, timedelta, timezone
from typing import Dict, Any, overload, Type

from apscheduler.triggers.interval import IntervalTrigger

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.watch_task import WatchTaskRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.handler.base import Handler
from nonebot_plugin_pixivbot.handler.watch import WatchUserIllustsHandler, WatchFollowingIllustsHandler
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model import WatchTask, WatchType
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.service.interval_task_worker import IntervalTaskWorker
from nonebot_plugin_pixivbot.utils.nonebot import get_bot_user_identifier

conf = context.require(Config)


@context.root.register_eager_singleton()
class Watchman(IntervalTaskWorker[WatchTask[T_UID, T_GID]]):
    tag = "watchman"

    _trigger_hasher_mapper = {
        WatchType.user_illusts: lambda args: args["user_id"],
        WatchType.following_illusts: lambda args: hash(args["sender_user_id"]),
    }

    @property
    def repo(self) -> WatchTaskRepo:
        return context.require(WatchTaskRepo)

    @classmethod
    def _get_handler_type(cls, type: WatchType) -> Type["Handler"]:
        if type == WatchType.user_illusts:
            return WatchUserIllustsHandler
        elif type == WatchType.following_illusts:
            return WatchFollowingIllustsHandler

    async def _handle_trigger(self, task: WatchTask[T_UID, T_GID], post_dest: PostDestination[T_UID, T_GID],
                              manually: bool = False):
        try:
            handler_type = self._get_handler_type(task.type)
            handler = handler_type(post_dest, silently=not manually, disable_interceptors=manually)
            await handler.handle_with_parsed_args(task=task)
        finally:
            # 保存checkpoint，避免一次异常后下一次重复推送
            # 但是会存在丢失推送的问题
            task.checkpoint = datetime.now(timezone.utc)
            await self.repo.update(task)

    def _make_job_trigger(self, item: WatchTask[T_UID, T_GID]) -> IntervalTrigger:
        hasher = self._trigger_hasher_mapper[item.type]
        hash_sec = hasher(item.kwargs) % conf.pixiv_watch_interval
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=-1) + timedelta(seconds=hash_sec)
        trigger = IntervalTrigger(seconds=conf.pixiv_watch_interval, start_date=yesterday)
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

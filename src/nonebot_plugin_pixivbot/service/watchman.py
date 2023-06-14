from datetime import datetime, timedelta, timezone
from typing import Dict, Any, overload, Type, TYPE_CHECKING

from apscheduler.triggers.interval import IntervalTrigger
from nonebot_plugin_session import Session

from .interval_task_worker import IntervalTaskWorker
from ..config import Config
from ..data.watch_task import WatchTaskRepo
from ..global_context import context
from ..model import WatchTask, WatchType

if TYPE_CHECKING:
    from ..handler.base import Handler

conf = context.require(Config)


@context.root.register_eager_singleton()
class Watchman(IntervalTaskWorker[WatchTask]):
    tag = "watchman"

    _trigger_hasher_mapper = {
        WatchType.user_illusts: lambda item: item.kwargs["user_id"],
        WatchType.following_illusts: lambda item: hash(item.subscriber.id1),
    }

    @property
    def repo(self) -> WatchTaskRepo:
        return context.require(WatchTaskRepo)

    @classmethod
    def _get_handler_type(cls, type: WatchType) -> Type["Handler"]:
        from ..handler.watch import WatchUserIllustsHandler, WatchFollowingIllustsHandler

        if type == WatchType.user_illusts:
            return WatchUserIllustsHandler
        elif type == WatchType.following_illusts:
            return WatchFollowingIllustsHandler

    async def _handle_trigger(self, item: WatchTask, manually: bool = False):
        try:
            handler_type = self._get_handler_type(item.type)
            handler = handler_type(item.subscriber, silently=not manually, disable_interceptors=manually)
            await handler.handle_with_parsed_args(task=item)
        finally:
            # 保存checkpoint，避免一次异常后下一次重复推送
            # 但是会存在丢失推送的问题
            item.checkpoint = datetime.now(timezone.utc)
            await self.repo.update(item)

    def _make_job_trigger(self, item: WatchTask) -> IntervalTrigger:
        hasher = self._trigger_hasher_mapper[item.type]
        hash_sec = hasher(item) % conf.pixiv_watch_interval
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=-1) + timedelta(seconds=hash_sec)
        trigger = IntervalTrigger(seconds=conf.pixiv_watch_interval, start_date=yesterday)
        return trigger

    async def _build_task(self, type_: WatchType,
                          kwargs: Dict[str, Any],
                          session: Session) -> WatchTask:
        return WatchTask(type=type_, kwargs=kwargs,
                         subscriber=session)

    @overload
    async def add_task(self, type_: WatchType,
                       kwargs: Dict[str, Any],
                       session: Session) -> bool:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        return await super().add_task(*args, **kwargs)

    async def fetch(self, code: str, session: Session) -> bool:
        task = await self.repo.get_by_code(session, code)
        if task is not None:
            await self._handle_trigger(task, manually=True)
            return True
        return False

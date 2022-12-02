from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from typing import Dict, Any, AsyncIterable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger, Bot
from nonebot.exception import ActionFailed

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source import with_session_scope
from nonebot_plugin_pixivbot.data.watch_task import WatchTaskRepo
from nonebot_plugin_pixivbot.handler.watch.following_illusts import WatchFollowingIllustsHandler
from nonebot_plugin_pixivbot.handler.watch.user_illusts import WatchUserIllustsHandler
from nonebot_plugin_pixivbot.model import PostIdentifier, WatchTask, WatchType
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from nonebot_plugin_pixivbot.service.pixiv_account_binder import PixivAccountBinder
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect, on_bot_disconnect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name


@context.inject
@context.root.register_eager_singleton()
class Watchman:
    conf = Inject(Config)
    apscheduler = Inject(AsyncIOScheduler)
    repo = Inject(WatchTaskRepo)
    binder = Inject(PixivAccountBinder)
    postman_mgr = Inject(PostmanManager)
    pd_factory_mgr = Inject(PostDestinationFactoryManager)
    auth_mgr = Inject(AuthenticatorManager)

    def __init__(self):
        on_bot_connect(with_session_scope(self.on_bot_connect), replay=True)
        on_bot_disconnect(with_session_scope(self.on_bot_disconnect))

    @staticmethod
    def _make_job_id(task: WatchTask[T_UID, T_GID]):
        return f'watchman {task.subscriber} {task.code}'

    _trigger_hasher_mapper = {
        WatchType.user_illusts: lambda args: args["user_id"],
        WatchType.following_illusts: lambda args: hash(args["sender_user_id"]),
    }

    _handlers = {
        WatchType.user_illusts: context.require(WatchUserIllustsHandler),
        WatchType.following_illusts: context.require(WatchFollowingIllustsHandler),
    }

    async def _on_trigger(self, task: WatchTask[T_UID, T_GID], post_dest: PostDestination[T_UID, T_GID],
                          manually: bool = False):
        logger.info(f"[watchman] triggered \"{task}\"")

        try:
            try:
                await self._handlers[task.type].handle_with_parsed_args(post_dest=post_dest, silently=not manually,
                                                                        task=task, disabled_interceptors=manually)
            finally:
                # 保存checkpoint，避免一次异常后下一次重复推送
                # 但是会存在丢失推送的问题
                task.checkpoint = datetime.now(timezone.utc)
                await self.repo.update(task)
        except ActionFailed as e:
            logger.error(f"[watchman] ActionFailed {e}")

            available = self.auth_mgr.available(post_dest)
            if isawaitable(available):
                available = await available

            if not available:
                logger.info(f"[watchman] {post_dest} is no longer available, removing all his tasks...")
                await self.unwatch_all_by_subscriber(post_dest.identifier)

    def _make_job_trigger(self, task: WatchTask):
        hasher = self._trigger_hasher_mapper[task.type]
        hash_sec = hasher(task.kwargs) % self.conf.pixiv_watch_interval
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=-1) + timedelta(seconds=hash_sec)
        trigger = IntervalTrigger(seconds=self.conf.pixiv_watch_interval, start_date=yesterday)
        return trigger

    def _add_job(self, task: WatchTask[T_UID, T_GID], post_dest: PostDestination[T_UID, T_GID]):
        job_id = self._make_job_id(task)
        trigger = self._make_job_trigger(task)
        self.apscheduler.add_job(self._on_trigger, id=job_id, trigger=trigger,
                                 args=[task, post_dest],
                                 max_instances=1)
        logger.success(f"[watchman] add job \"{task}\"")

    def _remove_job(self, task: WatchTask[T_UID, T_GID]):
        job_id = self._make_job_id(task)
        self.apscheduler.remove_job(job_id)
        logger.success(f"[watchman] remove job \"{task}\"")

    async def on_bot_connect(self, bot: Bot):
        adapter = get_adapter_name(bot)
        async for task in self.repo.get_by_adapter(adapter):
            pd = self.pd_factory_mgr.build(bot, task.subscriber.user_id, task.subscriber.group_id)
            self._add_job(task, pd)

    async def on_bot_disconnect(self, bot: Bot):
        adapter = get_adapter_name(bot)
        async for task in self.repo.get_by_adapter(adapter):
            try:
                self._remove_job(task)
            except Exception as e:
                logger.error(f"[watchman] error occurred when remove job \"{task}\"")
                logger.exception(e)

    async def watch(self, type_: WatchType,
                    kwargs: Dict[str, Any],
                    subscriber: PostDestination[T_UID, T_GID]) -> bool:
        task = WatchTask(type=type_, kwargs=kwargs, subscriber=subscriber.identifier)
        ok = await self.repo.insert(task)
        if ok:
            logger.success(f"[watchman] inserted subscription \"{task}\"")
            self._add_job(task, subscriber.normalized())
        return ok

    async def unwatch(self, type_: WatchType, code: int) -> bool:
        task = await self.repo.delete_one(type_, code)
        if task:
            logger.success(f"[scheduler] removed subscription \"{task}\"")
            self._remove_job(task)
            return True
        else:
            return False

    async def unwatch_all_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]):
        old = await self.repo.delete_many_by_subscriber(subscriber)
        for task in old:
            logger.success(f"[scheduler] removed subscription \"{task}\"")
            self._remove_job(task)

    def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[WatchTask]:
        return self.repo.get_by_subscriber(subscriber)

    async def fetch(self, code: str, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        task = await self.repo.get_by_code(post_dest.identifier, code)
        if task is not None:
            await self._on_trigger(task, post_dest, manually=True)
            return True
        return False

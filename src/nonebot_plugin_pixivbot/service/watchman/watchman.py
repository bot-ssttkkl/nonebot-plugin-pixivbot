from datetime import datetime, timedelta, timezone
from typing import Dict, Any, TypeVar, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nonebot import logger, Bot

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.watch_task_repo import WatchTaskRepo
from nonebot_plugin_pixivbot.enums import WatchType
from nonebot_plugin_pixivbot.model import Illust, PostIdentifier
from nonebot_plugin_pixivbot.model.message import IllustMessageModel
from nonebot_plugin_pixivbot.model.watch_task import WatchTask
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.protocol_dep.postman import PostmanManager
from nonebot_plugin_pixivbot.utils.errors import BadRequestError
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect, on_bot_disconnect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name
from .pkg_context import context
from .shared_agen import WatchmanSharedAsyncGeneratorManager, WatchmanSharedAgenIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]
ID = PostIdentifier[UID, GID]

headers = {
    WatchType.user_illusts: "您订阅的画师更新了",
    WatchType.following_illusts: "您关注的画师更新了"
}

trigger_hasher_mapper = {
    WatchType.user_illusts: lambda args: args["user_id"],
    WatchType.following_illusts: lambda args: args["user_id"],
}


@context.inject
@context.root.register_eager_singleton()
class Watchman:
    conf: Config
    apscheduler: AsyncIOScheduler
    repo: WatchTaskRepo
    postman_mgr: PostmanManager
    pd_factory_mgr: PostDestinationFactoryManager
    shared_agen: WatchmanSharedAsyncGeneratorManager

    def __init__(self):
        on_bot_connect(self.on_bot_connect, replay=True)
        on_bot_disconnect(self.on_bot_disconnect)

    async def _post_illust(self, illust: Illust, *,
                           header: Optional[str] = None,
                           post_dest: PD):
        model = await IllustMessageModel.from_illust(illust, header=header)
        if model is not None:
            await self.postman_mgr.send_illust(model, post_dest=post_dest)

    async def _handle(self, task: WatchTask, post_dest: PD):
        # logger.info(f"[watchman] handle user_illust {pixiv_user_id}")
        with self.shared_agen.get(WatchmanSharedAgenIdentifier(task.type, **task.kwargs)) as iter:
            async for illust in iter:
                if illust.create_date > task.checkpoint:
                    logger.info(f"[watchman] send illust {illust.id} to {task.subscriber}")
                    await self._post_illust(illust, header=headers.get(task.type, ""),
                                            post_dest=post_dest)
                else:
                    break

        task.checkpoint = datetime.now(timezone.utc)

        await self.repo.update(task)

    @staticmethod
    def _make_job_id(task: WatchTask):
        args = " ".join(map(lambda k: f'{k}={task.kwargs[k]}', task.kwargs))
        return f'watchman {task.type.name} {args} {task.subscriber}'

    def _make_job_trigger(self, task: WatchTask):
        hasher = trigger_hasher_mapper[task.type]
        hash_sec = hasher(task.kwargs) % self.conf.pixiv_watch_interval
        yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=-1) + timedelta(seconds=hash_sec)
        trigger = IntervalTrigger(seconds=self.conf.pixiv_watch_interval, start_date=yesterday)
        return trigger

    def _add_job(self, task: WatchTask, post_dest: PD):
        job_id = self._make_job_id(task)
        trigger = self._make_job_trigger(task)
        self.apscheduler.add_job(self._handle, id=job_id, trigger=trigger,
                                 args=[task, post_dest],
                                 max_instances=1)
        logger.success(f"[watchman] add job \"{job_id}\"")

    def _remove_job(self, task: WatchTask):
        job_id = self._make_job_id(task)
        self.apscheduler.remove_job(job_id)
        logger.success(f"[watchman] remove job \"{job_id}\"")

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
                logger.exception(e)

    async def watch(self, type: WatchType,
                    args: Dict[str, Any],
                    subscriber: PD):
        task = WatchTask(type=type, args=args, subscriber=subscriber.identifier)
        old_task = await self.repo.update(task)
        if old_task is not None:
            self._remove_job(old_task)
        self._add_job(task, subscriber.normalized())

    async def unwatch(self, type: WatchType,
                      args: Dict[str, Any],
                      subscriber: PD):
        old_task = await self.repo.get(type, args, subscriber.identifier)
        if old_task is not None:
            self._remove_job(old_task)
        else:
            raise BadRequestError("指定的订阅不存在")

    def get_by_subscriber(self, subscriber: ID):
        return self.repo.get_by_subscriber(subscriber)
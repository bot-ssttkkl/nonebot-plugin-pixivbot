from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Generic, TypeVar, AsyncIterable

from apscheduler.triggers.base import BaseTrigger
from nonebot import logger, Bot, get_bot
from nonebot.exception import ActionFailed
from nonebot_plugin_apscheduler import scheduler as apscheduler

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.interval_task_repo import IntervalTaskRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.model.interval_task import IntervalTask
from nonebot_plugin_pixivbot.protocol_dep.authenticator import AuthenticatorManager
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestinationFactoryManager, PostDestination
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect, on_bot_disconnect
from nonebot_plugin_pixivbot.utils.nonebot import get_bot_user_identifier

T = TypeVar("T", bound=IntervalTask)


@context.inject
class IntervalTaskWorker(ABC, Generic[T]):
    tag: str = ""

    pd_factory_mgr: PostDestinationFactoryManager = Inject(PostDestinationFactoryManager)
    auth_mgr: AuthenticatorManager = Inject(AuthenticatorManager)

    repo: IntervalTaskRepo[T]

    def __init__(self):
        @on_bot_connect(replay=True)
        async def _(bot: Bot):
            async for task in self.repo.get_by_bot(get_bot_user_identifier(bot)):
                try:
                    self._add_job(task)
                except Exception as e:
                    logger.error(f"[{self.tag}] error occurred when adding job for task \"{task}\"")
                    logger.exception(e)

        @on_bot_disconnect()
        async def _(bot: Bot):
            async for task in self.repo.get_by_bot(get_bot_user_identifier(bot)):
                try:
                    self._remove_job(task)
                except Exception as e:
                    logger.error(f"[{self.tag}] error occurred when removing job for task \"{task}\"")
                    logger.exception(e)

    @classmethod
    def _make_job_id(cls, item: T):
        return f'{cls.tag} {item.subscriber} {item.code}'

    @abstractmethod
    async def _handle_trigger(self, item: T, post_dest: PostDestination[T_UID, T_GID]):
        ...

    async def _on_trigger(self, item: T):
        logger.info(f"[{self.tag}] triggered \"{item}\"")

        bot = get_bot(item.bot.user_id)
        post_dest = self.pd_factory_mgr.build(bot, item.subscriber.user_id, item.subscriber.group_id)

        try:
            await self._handle_trigger(item, post_dest)
        except ActionFailed as e:
            logger.error(f"[{self.tag}] ActionFailed {e}")

            available = self.auth_mgr.available(post_dest)
            if isawaitable(available):
                available = await available

            if not available:
                logger.info(f"[{self.tag}] {post_dest} is no longer available, removing all his tasks...")
                await self.unwatch_all_by_subscriber(post_dest.identifier)

    @abstractmethod
    def _make_job_trigger(self, item: T) -> BaseTrigger:
        ...

    def _add_job(self, item: T):
        job_id = self._make_job_id(item)
        job_exists = apscheduler.get_job(job_id) is not None

        if not job_exists:
            trigger = self._make_job_trigger(item)

            apscheduler.add_job(self._on_trigger, id=job_id, trigger=trigger,
                                args=[item])
            logger.success(f"[{self.tag}] added job \"{job_id}\"")
        else:
            logger.debug(f"[{self.tag}] job \"{job_id}\" already exists")

    def _remove_job(self, item: T):
        job_id = self._make_job_id(item)
        apscheduler.remove_job(job_id)
        logger.success(f"[{self.tag}] removed job \"{item}\"")

    async def _get_permission(self, item: T) -> bool:
        ...

    async def _build_task(self, *args, **kwargs) -> T:
        ...

    async def add_task(self, *args, **kwargs) -> bool:
        item = await self._build_task(*args, **kwargs)
        ok = await self.repo.insert(item)
        if ok:
            logger.success(f"[{self.tag}] inserted task \"{item}\"")
            self._add_job(item)
        return ok

    async def remove_task(self, post_dest: PostDestination[T_UID, T_GID], code: str) -> bool:
        item = await self.repo.delete_one(get_bot_user_identifier(post_dest.bot),
                                          post_dest.identifier, code)
        if item:
            logger.success(f"[{self.tag}] removed task \"{item}\"")
            self._remove_job(item)
            return True
        else:
            return False

    async def unschedule_all_by_subscriber(self, post_dest: PostDestination[T_UID, T_GID]):
        old = await self.repo.delete_many_by_subscriber(get_bot_user_identifier(post_dest.bot),
                                                        post_dest.identifier)
        for item in old:
            logger.success(f"[{self.tag}] removed task \"{item}\"")
            self._remove_job(item)

    async def get_by_subscriber(self, post_dest: PostDestination[T_UID, T_GID]) -> AsyncIterable[T]:
        async for x in self.repo.get_by_subscriber(get_bot_user_identifier(post_dest.bot),
                                                   post_dest.identifier):
            yield x

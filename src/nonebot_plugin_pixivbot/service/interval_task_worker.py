from abc import ABC, abstractmethod
from typing import Generic, TypeVar, AsyncIterable

from apscheduler.triggers.base import BaseTrigger
from nonebot import logger, Bot
from nonebot.exception import ActionFailed
from nonebot_plugin_apscheduler import scheduler as apscheduler
from nonebot_plugin_session import Session, SessionIdType

from ..data.interval_task_repo import IntervalTaskRepo
from ..model.interval_task import IntervalTask
from ..platform import platform_func
from ..platform.func_manager import UnsupportedBotError
from ..utils.lifecycler import on_bot_connect, on_bot_disconnect

T = TypeVar("T", bound=IntervalTask)


class IntervalTaskWorker(ABC, Generic[T]):
    tag: str = ""

    @property
    @abstractmethod
    def repo(self) -> IntervalTaskRepo[T]:
        raise NotImplementedError()

    def __init__(self):
        @on_bot_connect(replay=True)
        async def _(bot: Bot):
            async for task in self.repo.get_by_bot(bot.self_id):
                try:
                    self._add_job(task)
                except Exception as e:
                    logger.opt(exception=e).error(f"[{self.tag}] error occurred when adding job for task \"{task}\"")

        @on_bot_disconnect()
        async def _(bot: Bot):
            async for task in self.repo.get_by_bot(bot.self_id):
                try:
                    self._remove_job(task)
                except Exception as e:
                    logger.opt(exception=e).error(f"[{self.tag}] error occurred when removing job for task \"{task}\"")

    @classmethod
    def _make_job_id(cls, item: T):
        return f'{cls.tag} {item.subscriber.get_id(SessionIdType.GROUP)} {item.code}'

    @abstractmethod
    async def _handle_trigger(self, item: T):
        ...

    async def _on_trigger(self, item: T):
        logger.info(f"[{self.tag}] triggered \"{item}\"")

        try:
            await self._handle_trigger(item)
        except ActionFailed as e:
            logger.opt(exception=e).error(f"[{self.tag}] action failed when handling task \"{item.code}\"")

            try:
                available = await platform_func(item.subscriber.bot_type).available(item.subscriber)
            except UnsupportedBotError:
                available = True

            if not available:
                logger.info(f"[{self.tag}] {item.subscriber} is no longer available, removing all his tasks...")
                await self.remove_all_by_subscriber(item.subscriber)

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

    async def _check_by_subject(self, item: T) -> bool:
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

    async def remove_task(self, session: Session, code: str) -> bool:
        item = await self.repo.delete_one(session, code)
        if item:
            logger.success(f"[{self.tag}] removed task \"{item}\"")
            self._remove_job(item)
            return True
        else:
            return False

    async def remove_all_by_subscriber(self, session: Session):
        old = await self.repo.delete_many_by_session(session)
        for item in old:
            logger.success(f"[{self.tag}] removed task \"{item}\"")
            self._remove_job(item)

    async def get_by_subscriber(self, session: Session) -> AsyncIterable[T]:
        async for x in self.repo.get_by_session(session):
            yield x

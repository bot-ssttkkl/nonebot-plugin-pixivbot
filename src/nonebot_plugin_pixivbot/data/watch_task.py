from datetime import datetime
from typing import Optional, AsyncIterable, Collection

from nonebot_plugin_session import Session
from pytz import utc
from sqlalchemy import select, UniqueConstraint, update
from sqlalchemy.orm import mapped_column, Mapped

from .interval_task_repo import IntervalTaskRepo, process_subscriber
from .nb_session import NbSessionRepo
from .source.sql import DataSource
from .utils.shortuuid import gen_code
from .utils.sql import insert, JSON, UTCDateTime
from ..global_context import context
from ..model import WatchType, WatchTask


@DataSource.registry.mapped
class WatchTaskOrm:
    __tablename__ = "watch_task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int]
    code: Mapped[str]
    type: Mapped[WatchType]
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    bot_id: Mapped[str]
    checkpoint: Mapped[datetime] = mapped_column(UTCDateTime)

    __table_args__ = (
        UniqueConstraint("bot_id", "session_id", "code"),
        UniqueConstraint("bot_id", "session_id", "type", "kwargs"),
    )


data_source = context.require(DataSource)
nb_session_repo = context.require(NbSessionRepo)


async def _to_model(item: WatchTaskOrm) -> WatchTask:
    subscriber = await nb_session_repo.get_session(item.session_id)
    return WatchTask(subscriber=subscriber,
                     code=item.code,
                     type=item.type,
                     kwargs=item.kwargs,
                     checkpoint=item.checkpoint)


@context.register_singleton()
class WatchTaskRepo(IntervalTaskRepo[WatchTask]):
    async def get_by_session(self, session: Session) -> AsyncIterable[WatchTask]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (
                select(WatchTaskOrm)
                .where(WatchTaskOrm.bot_id == session.bot_id,
                       WatchTaskOrm.session_id == session_id)
            )
            async for x in await db_sess.stream_scalars(stmt):
                x.checkpoint = x.checkpoint.replace(tzinfo=utc)
                yield await _to_model(x)

    async def get_by_bot(self, bot_id: str) -> AsyncIterable[WatchTask]:
        async with data_source.start_session() as db_sess:
            stmt = (
                select(WatchTaskOrm)
                .where(WatchTaskOrm.bot_id == bot_id)
            )
            async for x in await db_sess.stream_scalars(stmt):
                x.checkpoint = x.checkpoint.replace(tzinfo=utc)
                yield await _to_model(x)

    async def get_by_code(self, session: Session,
                          code: str) -> Optional[WatchTask]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot_id == session.bot_id,
                           WatchTaskOrm.session_id == session_id,
                           WatchTaskOrm.code == code))
            result = (await db_sess.execute(stmt)).scalar_one_or_none()
            result.checkpoint = result.checkpoint.replace(tzinfo=utc)
            return await _to_model(result)

    async def insert(self, item: WatchTask) -> bool:
        item.code = gen_code()
        item.subscriber = process_subscriber(item.subscriber)
        session_id = await nb_session_repo.get_id(item.subscriber)

        async with data_source.start_session() as db_session:
            stmt = (insert(WatchTaskOrm)
                    .values(session_id=session_id,
                            code=item.code,
                            type=item.type,
                            kwargs=item.kwargs,
                            bot_id=item.subscriber.bot_id,
                            checkpoint=item.checkpoint))
            stmt = stmt.on_conflict_do_nothing()
            result = await db_session.execute(stmt)
            await db_session.commit()

            return result.rowcount == 1

    async def update(self, item: WatchTask) -> bool:
        item.subscriber = process_subscriber(item.subscriber)
        session_id = await nb_session_repo.get_id(item.subscriber)
        async with data_source.start_session() as db_session:
            stmt = (update(WatchTaskOrm)
                    .values(type=item.type,
                            kwargs=item.kwargs,
                            bot_id=item.subscriber.bot_id,
                            checkpoint=item.checkpoint)
                    .where(WatchTaskOrm.session_id == session_id,
                           WatchTaskOrm.code == item.code))
            result = await db_session.execute(stmt)
            await db_session.commit()
            return result.rowcount == 1

    async def delete_one(self, session: Session, code: str) -> Optional[WatchTask]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot_id == session.bot_id,
                           WatchTaskOrm.session_id == session_id,
                           WatchTaskOrm.code == code)
                    .limit(1))
            task = (await db_sess.execute(stmt)).scalar_one_or_none()

            if task is None:
                return task

            await db_sess.delete(task)
            await db_sess.commit()
            return await _to_model(task)

    async def delete_many_by_session(self, session: Session) -> Collection[WatchTask]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (select(WatchTaskOrm)
                    .where(WatchTaskOrm.bot_id == session.bot_id,
                           WatchTaskOrm.session_id == session_id))
            tasks = (await db_sess.execute(stmt)).scalars().all()

            for t in tasks:
                await db_sess.delete(t)

            await db_sess.commit()
            return [await _to_model(x) for x in tasks]


__all__ = ("WatchTaskRepo",)

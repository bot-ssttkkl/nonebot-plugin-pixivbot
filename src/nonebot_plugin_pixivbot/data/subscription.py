from typing import Optional, AsyncIterable, Collection

import tzlocal
from nonebot_plugin_session import Session
from sqlalchemy import select, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from .interval_task_repo import IntervalTaskRepo, process_subscriber
from .nb_session import NbSessionRepo
from .source.sql import DataSource
from .utils.shortuuid import gen_code
from .utils.sql import insert, JSON
from ..global_context import context
from ..model import Subscription, ScheduleType
from ..model.subscription import IntervalSchedule, CronSchedule


@DataSource.registry.mapped
class SubscriptionOrm:
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int]
    code: Mapped[str]
    type: Mapped[ScheduleType]
    kwargs: Mapped[dict] = mapped_column(JSON, default=dict)
    bot_id: Mapped[str]
    schedule: Mapped[list] = mapped_column(JSON)
    tz: Mapped[str] = mapped_column(default=tzlocal.get_localzone_name)

    __table_args__ = (
        UniqueConstraint("bot_id", "session_id", "code"),
    )


data_source = context.require(DataSource)
nb_session_repo = context.require(NbSessionRepo)


async def _to_model(item: SubscriptionOrm) -> Subscription:
    subscriber = await nb_session_repo.get_session(item.session_id)
    if len(item.schedule) == 4:
        schedule = IntervalSchedule(*item.schedule)
    else:
        schedule = CronSchedule(*item.schedule)
    return Subscription(subscriber=subscriber,
                        code=item.code,
                        type=item.type,
                        kwargs=item.kwargs,
                        schedule=schedule,
                        tz=item.tz)


@context.register_singleton()
class SubscriptionRepo(IntervalTaskRepo[Subscription]):
    async def get_by_session(self, session: Session) -> AsyncIterable[Subscription]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.session_id == session_id)
            )
            async for x in await db_sess.stream_scalars(stmt):
                yield await _to_model(x)

    async def get_by_bot(self, bot_id: str) -> AsyncIterable[Subscription]:
        async with data_source.start_session() as db_sess:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.bot_id == bot_id)
            )
            async for x in await db_sess.stream_scalars(stmt):
                yield await _to_model(x)

    async def get_by_code(self, session: Session,
                          code: str) -> Optional[Subscription]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (
                select(SubscriptionOrm)
                .where(SubscriptionOrm.bot_id == session.bot_id,
                       SubscriptionOrm.session_id == session_id,
                       SubscriptionOrm.code == code)
            )
            x = (await db_sess.execute(stmt)).scalar_one_or_none()
            if x is not None:
                return await _to_model(x)
            else:
                return None

    async def insert(self, item: Subscription) -> bool:
        item.code = gen_code()
        item.subscriber = process_subscriber(item.subscriber)
        session_id = await nb_session_repo.get_id(item.subscriber)

        async with data_source.start_session() as db_sess:
            stmt = (insert(SubscriptionOrm)
                    .values(session_id=session_id,
                            code=item.code,
                            type=item.type,
                            kwargs=item.kwargs,
                            bot_id=item.subscriber.bot_id,
                            schedule=item.schedule,
                            tz=item.tz))
            await db_sess.execute(stmt)
            await db_sess.commit()
        return True

    async def delete_one(self, session: Session, code: str) -> Optional[Subscription]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (select(SubscriptionOrm)
                    .where(SubscriptionOrm.bot_id == session.bot_id,
                           SubscriptionOrm.session_id == session_id,
                           SubscriptionOrm.code == code)
                    .limit(1))
            sub = (await db_sess.execute(stmt)).scalar_one_or_none()

            if sub is None:
                return sub

            await db_sess.delete(sub)
            await db_sess.commit()
            return await _to_model(sub)

    async def delete_many_by_session(self, session: Session) -> Collection[Subscription]:
        session = process_subscriber(session)
        session_id = await nb_session_repo.get_id(session)
        async with data_source.start_session() as db_sess:
            stmt = (select(SubscriptionOrm)
                    .where(SubscriptionOrm.bot_id == session.bot_id,
                           SubscriptionOrm.session_id == session_id))
            subs = (await db_sess.execute(stmt)).scalars().all()

            for t in subs:
                await db_sess.delete(t)

            await db_sess.commit()
            return [await _to_model(x) for x in subs]


__all__ = ("SubscriptionRepo",)

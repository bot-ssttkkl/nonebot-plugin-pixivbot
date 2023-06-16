import json
from typing import Union

from nonebot_plugin_datastore.db import get_engine
from nonebot_plugin_session import Session, SessionLevel
from nonebot_plugin_session.model import get_or_add_session_model
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from nonebot_plugin_pixivbot import Config
from nonebot_plugin_pixivbot.global_context import context
from ...migration_manager import Migration


def convert_session(bot: str, subscriber: Union[str, bytes, dict]) -> Session:
    bot_adapter, bot_id = bot.split(":")

    if not isinstance(subscriber, dict):
        subscriber = json.loads(subscriber)

    if bot_adapter == "onebot":
        bot_type = "OneBot V11"
        platform = "qq"
        if subscriber["group_id"] is None:
            level = SessionLevel.LEVEL1
        else:
            level = SessionLevel.LEVEL2
    elif bot_adapter == "kaiheila":
        bot_type = "Kaiheila"
        platform = "kaiheila"
        if subscriber["group_id"] is None:
            level = SessionLevel.LEVEL1
        else:
            level = SessionLevel.LEVEL3
    elif bot_adapter == "telegram":
        bot_type = "Telegram"
        platform = "telegram"
        if subscriber["group_id"] is None:
            level = SessionLevel.LEVEL1
        else:
            level = SessionLevel.LEVEL3
    else:
        raise RuntimeError("Unknown adapter: " + bot_adapter)

    session = Session(bot_id=bot_id, bot_type=bot_type, platform=platform, level=level,
                      id1=subscriber["user_id"] or "0",
                      id2=subscriber["group_id"])
    return session


def convert_kwargs(kwargs):
    if not isinstance(kwargs, dict):
        kwargs = json.loads(kwargs)
    else:
        kwargs = {**kwargs}

    if "sender_user_id" in kwargs:
        kwargs["sender_user_id"] = str(kwargs["sender_user_id"])
    return kwargs


conf = context.require(Config)


class SqlV4ToV5(Migration):
    from_db_version = 4
    to_db_version = 5

    async def migrate(self, conn: AsyncConnection):
        # pixiv binding
        await conn.execute(text("alter table pixiv_binding rename to pixiv_binding_old;"))
        await conn.execute(text("""
            create table pixiv_binding
            (
                platform      VARCHAR not null,
                user_id       VARCHAR not null,
                pixiv_user_id INTEGER not null,
                primary key (platform, user_id)
            );
        """))
        await conn.execute(text("update pixiv_binding_old set adapter='qq' where adapter = 'onebot';"))
        await conn.execute(text("insert into pixiv_binding (platform, user_id, pixiv_user_id)"
                                "select adapter, user_id, pixiv_user_id from pixiv_binding_old;"))
        await conn.execute(text("drop table pixiv_binding_old;"))

        # subscription
        await conn.execute(text("alter table subscription rename to subscription_old;"))
        if conf.pixiv_sql_dialect == 'postgresql':
            await conn.execute(text("""
                create table subscription
                (
                    id         INTEGER     not null
                        primary key default nextval('subscription_id_seq'::regclass),
                    code       VARCHAR     not null,
                    session_id INTEGER     not null,
                    bot_id     VARCHAR     not null,
                    type       VARCHAR(25) not null,
                    kwargs     JSON        not null,
                    schedule   JSON        not null,
                    tz         VARCHAR     not null,
                    unique (bot_id, session_id, code)
                );
            """))
            await conn.execute(text("alter sequence subscription_id_seq owned by subscription.id;"))
        else:
            await conn.execute(text("""
                create table subscription
                (
                    id         INTEGER     not null
                        primary key autoincrement,
                    code       VARCHAR     not null,
                    session_id INTEGER     not null,
                    bot_id     VARCHAR     not null,
                    type       VARCHAR(25) not null,
                    kwargs     JSON        not null,
                    schedule   JSON        not null,
                    tz         VARCHAR     not null,
                    unique (bot_id, session_id, code)
                );
            """))

        async with AsyncSession(get_engine()) as db_sess:
            result = await conn.execute(
                text("select id, subscriber, code, type, kwargs, bot, schedule, tz from subscription_old;"))

            for id, subscriber, code, type, kwargs, bot, schedule, tz in result.fetchall():
                session = convert_session(bot, subscriber)
                session_id = (await get_or_add_session_model(session, db_sess)).id

                kwargs = convert_kwargs(kwargs)
                if not isinstance(kwargs, str):
                    kwargs = json.dumps(kwargs)

                await conn.execute(
                    text("insert into subscription(id, session_id, code, type, kwargs, bot_id, schedule, tz) "
                         "values (:id, :session_id, :code, :type, :kwargs, :bot_id, :schedule, :tz);"),
                    dict(id=id, session_id=session_id, code=code, type=type, kwargs=kwargs, bot_id=session.bot_id,
                         schedule=schedule, tz=tz)
                )

        await conn.execute(text("drop table subscription_old;"))

        # watch_task
        await conn.execute(text("alter table watch_task rename to watch_task_old;"))
        if conf.pixiv_sql_dialect == 'postgresql':
            await conn.execute(text("""
                CREATE TABLE watch_task (
                    id         INTEGER     not null
                        primary key default nextval('watch_task_id_seq'::regclass),
                    session_id INTEGER     not null,
                    code       VARCHAR     not null,
                    "type" watchtype NOT NULL,
                    kwargs jsonb NOT NULL,
                    bot_id     VARCHAR     not null,
                    "checkpoint" timestamp NOT NULL,
                    unique (bot_id, session_id, code),
                    unique (bot_id, session_id, type, kwargs)
                );
            """))
            await conn.execute(text("alter sequence watch_task_id_seq owned by watch_task.id;"))
        else:
            await conn.execute(text("""
                create table watch_task
                (
                    id         INTEGER     not null
                        primary key autoincrement,
                    session_id INTEGER     not null,
                    code       VARCHAR     not null,
                    type       VARCHAR(17) not null,
                    kwargs     JSON        not null,
                    bot_id     VARCHAR     not null,
                    checkpoint DATETIME    not null,
                    unique (bot_id, session_id, code),
                    unique (bot_id, session_id, type, kwargs)
                );
            """))

        async with AsyncSession(get_engine()) as db_sess:
            result = await conn.execute(
                text("select id, subscriber, code, type, kwargs, bot, checkpoint from watch_task_old;"))

            for id, subscriber, code, type, kwargs, bot, checkpoint in result.fetchall():
                session = convert_session(bot, subscriber)
                session_id = (await get_or_add_session_model(session, db_sess)).id

                kwargs = convert_kwargs(kwargs)

                if not isinstance(kwargs, str):
                    kwargs = json.dumps(kwargs)

                if not isinstance(schedule, str):
                    schedule = json.dumps(schedule)

                await conn.execute(
                    text("insert into watch_task(id, session_id, code, type, kwargs, bot_id, checkpoint) "
                         "values (:id, :session_id, :code, :type, :kwargs, :bot_id, :checkpoint);"),
                    dict(id=id, session_id=session_id, code=code, type=type, kwargs=kwargs, bot_id=session.bot_id,
                         checkpoint=checkpoint)
                )

        await conn.execute(text("drop table watch_task_old;"))

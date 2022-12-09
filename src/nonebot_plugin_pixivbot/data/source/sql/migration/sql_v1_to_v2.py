from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.global_context import context


class SqlV1ToV2:
    from_db_version = 1
    to_db_version = 2

    async def migrate(self, conn: AsyncConnection):
        conf = context.require(Config)
        if conf.pixiv_sql_dialect == 'sqlite':
            await conn.execute(text("""
            create table subscription_2
            (
                id         INTEGER     not null
                    primary key,
                subscriber JSON        not null,
                code       VARCHAR     not null,
                type       VARCHAR(25) not null,
                kwargs     JSON        not null,
                bot        VARCHAR     not null,
                schedule   JSON        not null,
                tz         VARCHAR     not null,
                unique (bot, subscriber, code)
            );
            """))
            await conn.execute(text("insert into subscription_2 (id, subscriber, code, type, kwargs, bot, schedule, tz)"
                                    "select id, subscriber, code, type, kwargs, adapter, schedule, tz from subscription;"))
            await conn.execute(text("drop table subscription;"))
            await conn.execute(text("alter table subscription_2 RENAME to subscription;"))

            await conn.execute(text("""
            create table watch_task_2
            (
                id         INTEGER     not null
                    primary key,
                subscriber JSON        not null,
                code       VARCHAR     not null,
                type       VARCHAR(17) not null,
                kwargs     JSON        not null,
                bot    VARCHAR     not null,
                checkpoint DATETIME    not null,
                unique (bot, subscriber, code),
                unique (bot, subscriber, type, kwargs)
            );
            """))
            await conn.execute(text("insert into watch_task_2 (id, subscriber, code, type, kwargs, bot, checkpoint)"
                                    "select id, subscriber, code, type, kwargs, adapter, checkpoint from watch_task;"))
            await conn.execute(text("drop table watch_task;"))
            await conn.execute(text("alter table watch_task_2 RENAME to watch_task;"))
        else:
            await conn.execute(text("drop index ix_watch_task_adapter;"))
            await conn.execute(text("alter table watch_task drop constraint watch_task_subscriber_code_key;"))
            await conn.execute(
                text("alter table watch_task drop constraint watch_task_subscriber_type_kwargs_key;"))
            await conn.execute(text("alter table watch_task rename column adapter to bot;"))
            await conn.execute(text("alter table watch_task add constraint watch_task_bot_subscriber_code_key "
                                    "unique (bot, subscriber, code);"))
            await conn.execute(
                text("alter table watch_task add constraint watch_task_bot_subscriber_type_kwargs_key "
                     "unique (bot, subscriber, type, kwargs);"))

            await conn.execute(text("drop index ix_subscription_adapter;"))
            await conn.execute(text("alter table subscription drop constraint subscription_subscriber_code_key;"))
            await conn.execute(text("alter table subscription rename column adapter to bot;"))
            await conn.execute(text("alter table subscription add constraint subscription_bot_subscriber_code_key "
                                    "unique (bot, subscriber, code);"))

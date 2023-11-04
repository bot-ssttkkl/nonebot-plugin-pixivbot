"""data_migrate

修订 ID: ec638b05408e
父修订: a52404f42561
创建时间: 2023-11-04 17:22:42.712867

"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic.op import run_async
from nonebot import logger
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection, create_async_engine
from ssttkkl_nonebot_utils.config_loader import load_conf

from nonebot_plugin_pixivbot import Config

revision: str = "ec638b05408e"
down_revision: str | Sequence[str] | None = "a52404f42561"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

conf = load_conf(Config)


async def data_migrate(conn: AsyncConnection):
    engine = create_async_engine(conf.pixiv_sql_conn_url)

    # nonebot_plugin_access_control_permission
    async with AsyncConnection(engine) as ds_conn:
        async with AsyncSession(ds_conn) as ds_sess:
            if not await ds_conn.run_sync(lambda conn: inspect(conn).has_table("meta_info")):
                return

            result = (await ds_sess.execute(
                sa.text(
                    "SELECT `value`, `key` "
                    "FROM meta_info "
                    "WHERE `key` = 'db_version'"
                )
            )).one_or_none()
            if result is None or result[0] != 5:
                raise RuntimeError(
                    "请先将 nonebot_plugin_pixivbot 降级至 2.1.0 版本，以将旧数据库迁移到最新版本")

            # local_tag
            result = await ds_sess.stream(
                sa.text(
                    "SELECT name, translated_name "
                    "FROM local_tag;"
                )
            )
            async for row in result:
                name, translated_name = row
                await conn.execute(
                    sa.text(
                        "INSERT INTO pixiv_local_tag (name, translated_name) "
                        "VALUES (:name, :translated_name);"
                    ),
                    [{"name": name, "translated_name": translated_name}],
                )
                logger.debug(
                    f"从表 local_tag 迁移数据："
                    f"name={name} translated_name={translated_name}"
                )

            # pixiv_binding
            result = await ds_sess.stream(
                sa.text(
                    "SELECT platform, user_id, pixiv_user_id "
                    "FROM pixiv_binding;"
                )
            )
            async for row in result:
                platform, user_id, pixiv_user_id = row
                await conn.execute(
                    sa.text(
                        "INSERT INTO pixivbot_pixiv_binding (platform, user_id, pixiv_user_id) "
                        "VALUES (:platform, :user_id, :pixiv_user_id);"
                    ),
                    [
                        {
                            "platform": platform,
                            "user_id": user_id,
                            "pixiv_user_id": pixiv_user_id,
                        }
                    ],
                )
                logger.debug(
                    f"从表 pixiv_binding 迁移数据："
                    f"platform={platform} user_id={user_id} pixiv_user_id={pixiv_user_id} "
                )

            # subscription
            result = await ds_sess.stream(
                sa.text(
                    "SELECT id, session_id, code, type, kwargs, bot_id, schedule, tz "
                    "FROM subscription;"
                )
            )
            async for row in result:
                id, session_id, code, type, kwargs, bot_id, schedule, tz = row
                await conn.execute(
                    sa.text(
                        "INSERT INTO pixivbot_subscription (id, session_id, code, type, kwargs, bot_id, schedule, tz) "
                        "VALUES (:id, :session_id, :code, :type, :kwargs, :bot_id, :schedule, :tz);"
                    ),
                    [
                        {
                            "id": id,
                            "session_id": session_id,
                            "code": code,
                            "type": type,
                            "kwargs": kwargs,
                            "bot_id": bot_id,
                            "schedule": schedule,
                            "tz": tz,
                        }
                    ],
                )
                logger.debug(
                    f"从表 subscription 迁移数据："
                    f"id={id} session_id={session_id} code={code} "
                    f"type={type} kwargs={kwargs} bot_id={bot_id} "
                    f"schedule={schedule} tz={tz}"
                )

            # subscription
            result = await ds_sess.stream(
                sa.text(
                    "SELECT id, session_id, code, type, kwargs, bot_id, schedule, tz "
                    "FROM subscription;"
                )
            )
            async for row in result:
                id, session_id, code, type, kwargs, bot_id, schedule, tz = row
                await conn.execute(
                    sa.text(
                        "INSERT INTO pixivbot_subscription (id, session_id, code, type, kwargs, bot_id, schedule, tz) "
                        "VALUES (:id, :session_id, :code, :type, :kwargs, :bot_id, :schedule, :tz);"
                    ),
                    [
                        {
                            "id": id,
                            "session_id": session_id,
                            "code": code,
                            "type": type,
                            "kwargs": kwargs,
                            "bot_id": bot_id,
                            "schedule": schedule,
                            "tz": tz,
                        }
                    ],
                )
                logger.debug(
                    f"从表 subscription 迁移数据："
                    f"id={id} session_id={session_id} code={code} "
                    f"type={type} kwargs={kwargs} bot_id={bot_id} "
                    f"schedule={schedule} tz={tz}"
                )

            # watch_task
            result = await ds_sess.stream(
                sa.text(
                    "SELECT id, session_id, code, type, kwargs, bot_id, checkpoint "
                    "FROM watch_task;"
                )
            )
            async for row in result:
                id, session_id, code, type, kwargs, bot_id, checkpoint = row
                await conn.execute(
                    sa.text(
                        "INSERT INTO pixivbot_watch_task (id, session_id, code, type, kwargs, bot_id, checkpoint) "
                        "VALUES (:id, :session_id, :code, :type, :kwargs, :bot_id, :checkpoint);"
                    ),
                    [
                        {
                            "id": id,
                            "session_id": session_id,
                            "code": code,
                            "type": type,
                            "kwargs": kwargs,
                            "bot_id": bot_id,
                            "checkpoint": checkpoint,
                        }
                    ],
                )
                logger.debug(
                    f"从表 watch_task 迁移数据："
                    f"id={id} session_id={session_id} code={code} "
                    f"type={type} kwargs={kwargs} bot_id={bot_id} "
                    f"checkpoint={checkpoint}"
                )


def upgrade(name: str = "") -> None:
    if name:
        return

    if conf.pixiv_sql_conn_url.startswith("sqlite+aiosqlite:///") and \
            not Path(conf.pixiv_sql_conn_url.removeprefix("sqlite+aiosqlite:///")).exists():
        return

    logger.info("正在从旧数据库迁移数据……")
    run_async(data_migrate)


def downgrade(name: str = "") -> None:
    # do nothing
    pass

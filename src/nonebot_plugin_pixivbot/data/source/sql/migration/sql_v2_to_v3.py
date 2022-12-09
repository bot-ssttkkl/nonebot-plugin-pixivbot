from nonebot import Bot, logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name


class SqlV2ToV3:
    from_db_version = 2
    to_db_version = 3
    deferred = True

    async def migrate(self, conn: AsyncConnection):
        data_source = context.require(SqlDataSource)

        @on_bot_connect(replay=True, first=True)
        async def _(bot: Bot):
            async with AsyncConnection(data_source.engine) as conn:
                adapter = get_adapter_name(bot)
                await conn.execute(
                    text(f"update watch_task set bot=bot || '\:{bot.self_id}' where bot = '{adapter}'; ")
                )
                await conn.execute(
                    text(f"update subscription set bot=bot || '\:{bot.self_id}' where bot = '{adapter}'; ")
                )
                await conn.commit()

        @data_source.on_closing
        async def _():
            async with AsyncConnection(data_source.engine) as conn:
                stmt = text("select count(*) from subscription where bot not like '%:%'")
                cnt = (await conn.execute(stmt)).scalar()
                if cnt != 0:
                    return

                stmt = text("select count(*) from watch_task where bot not like '%:%'")
                cnt = (await conn.execute(stmt)).scalar()
                if cnt != 0:
                    return

                await data_source._raw_set_db_version(conn, 3)
                await conn.commit()
                logger.success("set db_version=3")

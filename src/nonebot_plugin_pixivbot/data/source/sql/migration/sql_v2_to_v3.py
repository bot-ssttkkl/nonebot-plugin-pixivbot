from typing import Callable, Awaitable

from nonebot import Bot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from ...migration_manager import DeferrableMigration
from ...sql import DataSource
from .....global_context import context
from .....utils.lifecycler import on_bot_connect
from .....utils.nonebot import get_adapter_name


class SqlV2ToV3(DeferrableMigration):
    from_db_version = 2
    to_db_version = 3
    safe = True

    async def migrate(self, conn: AsyncConnection, on_migrated: Callable[[], Awaitable[None]]):
        data_source = context.require(DataSource)

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

                await on_migrated()

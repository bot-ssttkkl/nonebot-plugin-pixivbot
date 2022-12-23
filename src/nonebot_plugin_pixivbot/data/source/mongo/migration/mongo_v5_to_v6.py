from typing import Callable, Awaitable

from motor.motor_asyncio import AsyncIOMotorDatabase
from nonebot import Bot

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name
from .. import MongoDataSource
from ...migration_manager import DeferrableMigration


class MongoV5ToV6(DeferrableMigration):
    from_db_version = 5
    to_db_version = 6

    async def migrate(self, conn: AsyncIOMotorDatabase, on_migrated: Callable[[], Awaitable[None]]):
        data_source = context.require(MongoDataSource)

        @on_bot_connect(replay=True, first=True)
        async def _(bot: Bot):
            async with data_source.start_session() as session:
                adapter = get_adapter_name(bot)
                await data_source.db["subscription"].update_many(
                    {"subscriber.adapter": adapter},
                    [
                        {
                            "$set": {
                                "bot": {
                                    "adapter": adapter,
                                    "user_id": bot.self_id
                                }
                            },
                        }
                    ],
                    session=session
                )
                await data_source.db["watch_task"].update_many(
                    {"subscriber.adapter": adapter},
                    [
                        {
                            "$set": {
                                "bot": {
                                    "adapter": adapter,
                                    "user_id": bot.self_id
                                }
                            },
                        }
                    ],
                    session=session
                )

        @data_source.on_closing
        async def _():
            async with data_source.start_session() as session:
                async for x in data_source.db["subscription"].aggregate(
                        {
                            "$group": {
                                "_id": {
                                    "$gt": ["$bot", None]
                                }
                            },
                            "count": {
                                "$sum": 1
                            }
                        },
                        session=session
                ):
                    if (not x["_id"]) and x["count"] > 0:
                        return

                async for x in data_source.db["watch_task"].aggregate(
                        {
                            "$group": {
                                "_id": {
                                    "$gt": ["$bot", None]
                                }
                            },
                            "count": {
                                "$sum": 1
                            }
                        },
                        session=session
                ):
                    if (not x["_id"]) and x["count"] > 0:
                        return

            await on_migrated()

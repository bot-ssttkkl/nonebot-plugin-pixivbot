from motor.motor_asyncio import AsyncIOMotorDatabase
from nonebot import Bot, logger

from nonebot_plugin_pixivbot.data.source.mongo import MongoDataSource
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.utils.lifecycler import on_bot_connect
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name


class MongoV5ToV6:
    from_db_version = 5
    to_db_version = 6
    deffered = True

    async def migrate(self, conn: AsyncIOMotorDatabase):
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

            await data_source._raw_set_db_version(data_source.db, 6)
            logger.success("set db_version=6")

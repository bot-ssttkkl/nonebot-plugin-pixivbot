from motor.motor_asyncio import AsyncIOMotorDatabase

from ....utils.shortuuid import gen_code


class MongoV4ToV5:
    from_db_version = 4
    to_db_version = 5

    async def migrate(self, conn: AsyncIOMotorDatabase):
        await self.migrate_subscription(conn)
        await self.migrate_watch_task(conn)

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("subscriber_1_type_1")
        except:
            pass

        async for sub in db["subscription"].find():
            code = gen_code()
            await db["subscription"].update_one(sub, {"$set": {"code": code}})

    async def migrate_watch_task(self, db: AsyncIOMotorDatabase):
        try:
            await db["watch_task"].drop_index("subscriber_1_type_1_kwargs_1")
        except:
            pass

        async for sub in db["watch_task"].find():
            code = gen_code()
            await db["watch_task"].update_one(sub, {"$set": {"code": code}})

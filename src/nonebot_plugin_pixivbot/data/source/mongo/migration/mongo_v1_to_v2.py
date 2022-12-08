from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoV1ToV2:
    from_db_version = 1
    to_db_version = 2

    async def migrate(self, conn: AsyncIOMotorDatabase):
        await self.migrate_pixiv_binding(conn)
        await self.migrate_subscription(conn)

    async def migrate_pixiv_binding(self, db: AsyncIOMotorDatabase):
        try:
            await db["pixiv_binding"].drop_index("qq_id_1")
        except:
            pass

        # 先drop index，否则报duplicate key

        await db["pixiv_binding"].update_many(
            {},
            [
                {"$set": {"adapter": "onebot", "user_id": "$qq_id"}},
                {"$unset": ["qq_id"]}
            ]
        )

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("user_id_1")
        except:
            pass

        try:
            await db["subscription"].drop_index("group_id_1")
        except:
            pass

        try:
            await db["subscription"].drop_index("type_1_user_id_1")
        except:
            pass

        try:
            await db["subscription"].drop_index("type_1_group_id_1")
        except:
            pass

        await db["subscription"].update_many(
            {},
            {"$set": {"adapter": "onebot"}}
        )


__all__ = ("MongoV1ToV2",)

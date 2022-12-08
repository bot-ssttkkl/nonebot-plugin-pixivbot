from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoV3ToV4:
    from_db_version = 3
    to_db_version = 4

    async def migrate(self, conn: AsyncIOMotorDatabase):
        await self.migrate_subscription(conn)

    async def migrate_subscription(self, db: AsyncIOMotorDatabase):
        try:
            await db["subscription"].drop_index("adapter_1_group_id_1_type_1")
        except:
            pass

        try:
            await db["subscription"].drop_index("adapter_1_user_id_1_type_1")
        except:
            pass

        await db["subscription"].update_many(
            {},
            [
                {
                    "$set": {
                        "subscriber": {
                            "$let": {
                                "vars": {
                                    "adapter": "$$ROOT.adapter",
                                    "user_id": "$$ROOT.user_id",
                                    "group_id": "$$ROOT.group_id",
                                },
                                "in": {
                                    "adapter": {
                                        "$cond": {
                                            "if": {"$ne": [{"$type": "$$adapter"}, "missing"]},
                                            "then": "$$adapter",
                                            "else": None
                                        },
                                    },
                                    "user_id": {
                                        "$cond": {
                                            "if": {"$ne": [{"$type": "$$user_id"}, "missing"]},
                                            "then": "$$user_id",
                                            "else": None
                                        },
                                    },
                                    "group_id": {
                                        "$cond": {
                                            "if": {"$ne": [{"$type": "$$group_id"}, "missing"]},
                                            "then": "$$group_id",
                                            "else": None
                                        },
                                    }
                                }
                            }
                        },
                        "tz": "Asia/Shanghai"
                    }
                },
                {
                    "$unset": [
                        "adapter",
                        "user_id",
                        "group_id"
                    ]
                }
            ]
        )

from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoMigration(ABC):
    from_db_version: int
    to_db_version: int

    @abstractmethod
    async def migrate(self, client: AsyncIOMotorDatabase):
        raise NotImplementedError()

from motor.motor_asyncio import AsyncIOMotorDatabase

from .mongo_v1_to_v2 import MongoV1ToV2
from .mongo_v2_to_v3 import MongoV2ToV3
from .mongo_v3_to_v4 import MongoV3ToV4
from .mongo_v4_to_v5 import MongoV4ToV5
from .mongo_v5_to_v6 import MongoV5ToV6
from ...migration_manager import Migration, MigrationManager

mongo_migration_manager = MigrationManager[Migration[AsyncIOMotorDatabase]]()
mongo_migration_manager.add(MongoV1ToV2)
mongo_migration_manager.add(MongoV2ToV3)
mongo_migration_manager.add(MongoV3ToV4)
mongo_migration_manager.add(MongoV4ToV5)
mongo_migration_manager.add(MongoV5ToV6)

from typing import Callable, Awaitable

from .mongo_v1_to_v2 import MongoV1ToV2
from .mongo_v2_to_v3 import MongoV2ToV3
from .mongo_v3_to_v4 import MongoV3ToV4
from .mongo_v4_to_v5 import MongoV4ToV5
from .mongo_v5_to_v6 import MongoV5ToV6
from .mongo_v6_to_v7 import MongoV6ToV7
from ...migration_manager import MigrationManager


class MongoMigrationManager(MigrationManager):
    def __init__(self, on_migrated: Callable[[int, int], Awaitable[None]]):
        super().__init__(on_migrated)
        self.add(MongoV1ToV2)
        self.add(MongoV2ToV3)
        self.add(MongoV3ToV4)
        self.add(MongoV4ToV5)
        self.add(MongoV5ToV6)
        self.add(MongoV6ToV7)

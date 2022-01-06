import typing
from ..config import conf
from pymongo import MongoClient, ReturnDocument
from .mongo_conn import mongo_client


class Subscriptions:
    db_name: str

    def __init__(self, db_name: str):
        self.db_name = db_name

    @property
    def _db(self) -> MongoClient:
        return mongo_client()[self.db_name]

    def get(self, user_id: typing.Optional[int] = None,
            group_id: typing.Optional[int] = None):
        if user_id is None and group_id is None:
            query = {}
        elif user_id is None and group_id is not None:
            query = {"group_id": group_id}
        elif user_id is not None and group_id is None:
            query = {"user_id": user_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        return self._db.subscription.find(query)

    def update(self, type: str,
               schedule: typing.Sequence[int],
               user_id: typing.Optional[int] = None,
               group_id: typing.Optional[int] = None,
               **kwargs):
        if user_id is None and group_id is not None:
            query = {"type": type, "group_id": group_id}
        elif user_id is not None and group_id is None:
            query = {"type": type, "user_id": user_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        return self._db.subscription.find_one_and_replace(query, {**query,
                                                                  "schedule": schedule,
                                                                  "kwargs": kwargs},
                                                          return_document=ReturnDocument.BEFORE,
                                                          upsert=True)

    def delete(self, type: str,
               user_id: typing.Optional[int] = None,
               group_id: typing.Optional[int] = None):
        if user_id is None and group_id is not None:
            query = {"type": type, "user_id": user_id}
        elif user_id is not None and group_id is None:
            query = {"type": type, "group_id": group_id}
        else:
            raise ValueError("Both user_id and group_id are not None.")

        if type != 'all':
            return self._db.subscription.delete_one(query)
        else:
            del query["type"]
            return self._db.subscription.delete_many(query)


subscriptions = Subscriptions(conf.pixiv_mongo_database_name)

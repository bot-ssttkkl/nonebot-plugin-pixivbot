import typing

from pymongo import ReturnDocument

from .mongo_conn import db
from .pkg_context import context


@context.export_singleton()
class Subscriptions:
    def get(self, user_id: typing.Optional[int] = None,
            group_id: typing.Optional[int] = None):
        if group_id:
            query = {"group_id": group_id}
        elif user_id:
            query = {"user_id": user_id}
        else:
            raise ValueError("Both user_id and group_id are None.")

        return db().subscription.find(query)

    def get_all(self):
        return db().subscription.find()

    def update(self, type: str,
               user_id: typing.Optional[int] = None,
               group_id: typing.Optional[int] = None,
               *, schedule: typing.Sequence[int],
               kwargs: dict = {}):
        if group_id:
            query = {"group_id": group_id, "type": type}
        elif user_id:
            query = {"user_id": user_id, "type": type}
        else:
            raise ValueError("Both user_id and group_id are None.")

        return db().subscription.find_one_and_replace(query, {**query,
                                                              "schedule": schedule,
                                                              "kwargs": kwargs},
                                                      return_document=ReturnDocument.BEFORE,
                                                      upsert=True)

    def delete(self, type: str,
               user_id: typing.Optional[int] = None,
               group_id: typing.Optional[int] = None):
        if group_id:
            query = {"group_id": group_id, "type": type}
        elif user_id:
            query = {"user_id": user_id, "type": type}
        else:
            raise ValueError("Both user_id and group_id are None.")

        if type != 'all':
            return db().subscription.delete_one(query)
        else:
            del query["type"]
            return db().subscription.delete_many(query)


__all__ = ("Subscriptions", )

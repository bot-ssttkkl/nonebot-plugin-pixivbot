import typing

from pymongo import *

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Tag
from .source import MongoDataSource


@context.inject
@context.register_singleton()
class LocalTagRepo:
    mongo: MongoDataSource

    async def insert(self, tag: Tag) -> typing.NoReturn:
        await self.mongo.db.local_tags.updateOne(
            {"name": tag.name},
            {"$setOnInsert": {"translated_name": tag.translated_name}},
            upsert=True
        )

    async def insert_many(self, tags: typing.Iterable[Tag]) -> typing.NoReturn:
        opt = []

        for tag in tags:
            opt.append(UpdateOne(
                {"name": tag.name},
                {"$setOnInsert": {"translated_name": tag.translated_name}},
                upsert=True
            ))

        if len(opt) != 0:
            await self.mongo.db.local_tags.bulk_write(opt, ordered=False)

    async def get_by_name(self, name: str) -> typing.Optional[Tag]:
        result = await self.mongo.db.local_tags.find_one({"name": name})
        if result:
            return Tag.parse_obj(result)
        else:
            return None

    async def get_by_translated_name(self, translated_name: str) -> typing.Optional[Tag]:
        result = await self.mongo.db.local_tags.find_one({"translated_name": translated_name})
        if result:
            return Tag.parse_obj(result)
        else:
            return None


__all__ = ("LocalTagRepo",)

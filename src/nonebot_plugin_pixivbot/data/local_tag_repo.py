from typing import Optional, Iterable

from beanie import Document
from beanie.odm.operators.update.general import SetOnInsert
from pymongo import *

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Tag
from .source import MongoDataSource


class LocalTag(Tag, Document):
    class Settings:
        name = "local_tags"
        indexes = [
            IndexModel([("name", 1)], unique=True),
            IndexModel([("translated_name", 1)])
        ]


context.require(MongoDataSource).document_models.append(LocalTag)


@context.inject
@context.register_singleton()
class LocalTagRepo:
    mongo: MongoDataSource

    @classmethod
    async def find_by_name(cls, name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.name == name)
        return result

    @classmethod
    async def find_by_translated_name(cls, translated_name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.translated_name == translated_name)
        return result

    @classmethod
    async def update_one(cls, tag: Tag):
        await LocalTag.find_one(LocalTag.name == tag.name).upsert(
            SetOnInsert({LocalTag.translated_name: tag.translated_name}),
            on_insert=LocalTag(**tag.dict()),
        )

    async def update_many(self, tags: Iterable[Tag]):
        # BulkWriter存在bug，upsert不生效
        # https://github.com/roman-right/beanie/issues/224
        #
        # async with BulkWriter() as bw:
        #     for tag in tags:
        #         await LocalTag.find_one(LocalTag.name == tag.name).upsert(
        #             SetOnInsert({LocalTag.translated_name: tag.translated_name}),
        #             on_insert=LocalTag(**tag.dict()),
        #             bulk_writer=bw
        #         )

        opt = []

        for tag in tags:
            opt.append(UpdateOne(
                {"name": tag.name},
                {"$setOnInsert": {"translated_name": tag.translated_name}},
                upsert=True
            ))

        if len(opt) != 0:
            await self.mongo.db.local_tags.bulk_write(opt, ordered=False)


__all__ = ("LocalTagRepo",)

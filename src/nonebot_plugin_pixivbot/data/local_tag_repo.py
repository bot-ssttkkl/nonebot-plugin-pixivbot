from typing import Optional, Iterable

from beanie import Document, BulkWriter
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


@context.register_singleton()
class LocalTagRepo:
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

    @classmethod
    async def update_many(cls, tags: Iterable[Tag]):
        async with BulkWriter() as bw:
            for tag in tags:
                await LocalTag.find_one(LocalTag.name == tag.name).upsert(
                    SetOnInsert({LocalTag.translated_name: tag.translated_name}),
                    on_insert=LocalTag(**tag.dict()),
                    bulk_writer=bw
                )


__all__ = ("LocalTagRepo",)

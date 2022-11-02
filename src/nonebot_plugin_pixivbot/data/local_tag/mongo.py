from typing import Optional, Collection

from beanie import Document
from beanie.odm.operators.update.general import SetOnInsert
from nonebot import logger
from pymongo import *

from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Tag, Illust
from ..source.mongo import MongoDataSource


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
class MongoLocalTagRepo:
    mongo = Inject(MongoDataSource)

    async def find_by_name(self, name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.name == name)
        return result

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.translated_name == translated_name)
        return result

    async def update_one(self, tag: Tag):
        await LocalTag.find_one(LocalTag.name == tag.name).upsert(
            SetOnInsert({LocalTag.translated_name: tag.translated_name}),
            on_insert=LocalTag(**tag.dict()),
        )

    async def update_many(self, tags: Collection[Tag]):
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
            logger.info(f"[local_tag_repo] added {len(tags)} local tags")

    async def update_from_illusts(self, illusts: Collection[Illust]):
        tags = {}
        for x in illusts:
            for t in x.tags:
                if t.translated_name:
                    tags[t.name] = t

        await self.update_many(tags.values())


__all__ = ("MongoLocalTagRepo",)

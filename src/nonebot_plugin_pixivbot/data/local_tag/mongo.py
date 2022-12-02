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
    mongo: MongoDataSource = Inject(MongoDataSource)

    async def find_by_name(self, name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.name == name, session=self.mongo.session())
        return result

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        result = await LocalTag.find_one(LocalTag.translated_name == translated_name, session=self.mongo.session())
        return result

    async def update_one(self, tag: Tag):
        session = self.mongo.session()

        await LocalTag.find_one(LocalTag.name == tag.name, session=session).upsert(
            SetOnInsert({LocalTag.translated_name: tag.translated_name}),
            on_insert=LocalTag(**tag.dict()),
            session=session
        )

    async def update_many(self, tags: Collection[Tag]):
        session = self.mongo.session()

        # BulkWriter存在bug，upsert不生效
        # https://github.com/roman-right/beanie/issues/224

        opt = []

        for tag in tags:
            opt.append(UpdateOne(
                {"name": tag.name},
                {"$setOnInsert": {"translated_name": tag.translated_name}},
                upsert=True
            ))

        if len(opt) != 0:
            await LocalTag.get_motor_collection().bulk_write(opt, ordered=False, session=session)
            logger.info(f"[local_tag_repo] added {len(tags)} local tags")

    async def update_from_illusts(self, illusts: Collection[Illust]):
        tags = {}
        for x in illusts:
            for t in x.tags:
                if t.translated_name:
                    tags[t.name] = t

        await self.update_many(tags.values())


__all__ = ("MongoLocalTagRepo",)

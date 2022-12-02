from typing import Optional, Collection

from nonebot import logger
from sqlalchemy import Column, String, select

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.sql import insert
from nonebot_plugin_pixivbot.model import Tag, Illust


@context.require(SqlDataSource).registry.mapped
class LocalTag:
    __tablename__ = "local_tag"

    name = Column(String, primary_key=True, nullable=False)
    translated_name = Column(String, nullable=False, index=True)


@context.inject
@context.register_singleton()
class SqlLocalTagRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def find_by_name(self, name: str) -> Optional[Tag]:
        session = self.data_source.session()
        stmt = select(LocalTag).where(LocalTag.name == name).limit(1)
        local_tag = (await session.execute(stmt)).scalar_one_or_none()
        if local_tag is not None:
            return Tag.from_orm(local_tag)
        else:
            return None

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        session = self.data_source.session()
        stmt = select(LocalTag).where(LocalTag.translated_name == translated_name).limit(1)
        local_tag = (await session.execute(stmt)).scalar_one_or_none()
        if local_tag is not None:
            return Tag.from_orm(local_tag)
        else:
            return None

    async def update_one(self, tag: Tag):
        await self.update_many([tag])

    async def update_many(self, tags: Collection[Tag]):
        if len(tags) == 0:
            return

        session = self.data_source.session()
        stmt = insert(LocalTag).values([t.dict() for t in tags])
        stmt = stmt.on_conflict_do_update(index_elements=[LocalTag.name],
                                          set_={
                                              LocalTag.translated_name: stmt.excluded.translated_name
                                          })

        await session.execute(stmt)
        await session.commit()
        logger.info(f"[local_tag_repo] added {len(tags)} local tags")

    async def update_from_illusts(self, illusts: Collection[Illust]):
        tags = {}
        for x in illusts:
            for t in x.tags:
                if t.translated_name:
                    tags[t.name] = t

        await self.update_many(tags.values())


__all__ = ("SqlLocalTagRepo",)

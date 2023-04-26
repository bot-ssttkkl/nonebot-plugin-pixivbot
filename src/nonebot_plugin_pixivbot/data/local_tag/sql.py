from typing import Optional, Collection

from nonebot import logger
from sqlalchemy import select
from sqlalchemy.orm import mapped_column, Mapped

from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.sql import insert
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import Tag, Illust
from .base import LocalTagRepo


@SqlDataSource.registry.mapped
class LocalTag:
    __tablename__ = "local_tag"

    name: Mapped[str] = mapped_column(primary_key=True)
    translated_name: Mapped[str] = mapped_column(index=True)


data_source = context.require(SqlDataSource)


@context.register_singleton()
class SqlLocalTagRepo(LocalTagRepo):

    async def find_by_name(self, name: str) -> Optional[Tag]:
        async with data_source.start_session() as session:
            stmt = select(LocalTag).where(LocalTag.name == name).limit(1)
            local_tag = (await session.execute(stmt)).scalar_one_or_none()
            if local_tag is not None:
                return Tag.from_orm(local_tag)
            else:
                return None

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        async with data_source.start_session() as session:
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

        async with data_source.start_session() as session:
            stmt = insert(LocalTag).values([t.dict() for t in tags])
            stmt = stmt.on_conflict_do_update(index_elements=[LocalTag.name],
                                              set_={
                                                  LocalTag.translated_name: stmt.excluded.translated_name
                                              })

            await session.execute(stmt)
            await session.commit()
            logger.debug(f"[local_tag_repo] added {len(tags)} local tags")

    async def update_from_illusts(self, illusts: Collection[Illust]):
        tags = {}
        for x in illusts:
            for t in x.tags:
                if t.translated_name:
                    tags[t.name] = t

        await self.update_many(tags.values())


__all__ = ("SqlLocalTagRepo",)

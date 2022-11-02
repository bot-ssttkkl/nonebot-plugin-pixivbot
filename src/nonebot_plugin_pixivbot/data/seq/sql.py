from sqlalchemy import Column, Integer, select, String
from sqlalchemy.dialects.sqlite import insert

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource


@context.require(SqlDataSource).registry.mapped
class Seq:
    __tablename__ = "seq"

    key: str = Column(String, primary_key=True, nullable=False)
    value: int = Column(Integer, nullable=False, default=0)


@context.inject
@context.register_singleton()
class SqlSeqRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def inc_and_get(self, key: str) -> int:
        session = self.data_source.session()
        stmt = (insert(Seq)
                .values(key=key, value=1)
                .on_conflict_do_update(index_elements=[Seq.key],
                                       set_={
                                           Seq.value: Seq.value + 1
                                       }))
        await session.execute(stmt)

        stmt = select(Seq).where(Seq.key == key)
        seq = (await session.execute(stmt)).scalar_one()
        return seq.value

    async def get_and_inc(self, key: str) -> int:
        return await self.inc_and_get(key) - 1

    async def get(self, key: str) -> int:
        session = self.data_source.session()
        stmt = select(Seq).where(Seq.key == key)
        seq = (await session.execute(stmt)).scalar_one_or_none()

        if seq is not None:
            return seq.value
        else:
            return 0

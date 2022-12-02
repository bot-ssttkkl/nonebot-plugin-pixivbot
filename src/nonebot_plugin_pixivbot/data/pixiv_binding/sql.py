from typing import Optional

from sqlalchemy import Column, String, Integer, select, delete

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.data.source.sql import SqlDataSource
from nonebot_plugin_pixivbot.data.utils.sql import insert
from nonebot_plugin_pixivbot.model import PixivBinding, T_UID


@context.require(SqlDataSource).registry.mapped
class PixivBindingOrm:
    __tablename__ = "pixiv_binding"

    adapter = Column(String, nullable=False, primary_key=True)
    user_id = Column(String, nullable=False, primary_key=True)
    pixiv_user_id = Column(Integer, nullable=False)


@context.inject
@context.register_singleton()
class SqlPixivBindingRepo:
    data_source: SqlDataSource = Inject(SqlDataSource)

    async def get(self, adapter: str, user_id: T_UID) -> Optional[PixivBinding]:
        session = self.data_source.session()
        stmt = (select(PixivBindingOrm)
                .where(PixivBindingOrm.adapter == adapter,
                       PixivBindingOrm.user_id == str(user_id))
                .limit(1))
        result = (await session.execute(stmt)).scalar_one_or_none()
        if result is not None:
            return PixivBinding(adapter=result.adapter,
                                user_id=type(user_id)(result.user_id),
                                pixiv_user_id=result.pixiv_user_id)
        else:
            return None

    async def update(self, binding: PixivBinding[T_UID]):
        session = self.data_source.session()
        stmt = (insert(PixivBindingOrm)
                .values(adapter=binding.adapter,
                        user_id=str(binding.user_id),
                        pixiv_user_id=binding.pixiv_user_id)
                .on_conflict_do_update(index_elements=[PixivBindingOrm.adapter, PixivBindingOrm.user_id],
                                       set_={
                                           PixivBindingOrm.pixiv_user_id: binding.pixiv_user_id
                                       }))
        await session.execute(stmt)
        await session.commit()

    async def remove(self, adapter: str, user_id: T_UID) -> bool:
        session = self.data_source.session()
        stmt = (delete(PixivBinding)
                .where(PixivBindingOrm.adapter == adapter,
                       PixivBindingOrm.user_id == str(user_id)))
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount == 1


__all__ = ("SqlPixivBindingRepo",)

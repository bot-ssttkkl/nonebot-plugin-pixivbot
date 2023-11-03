from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy import select, delete
from sqlalchemy.orm import Mapped, mapped_column

from .utils.session import use_pixivbot_session
from .sql_common import insert
from ..global_context import context
from ..model import PixivBinding


class PixivBindingOrm(Model):
    __tablename__ = "pixivbot_pixiv_binding"

    platform: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)
    pixiv_user_id: Mapped[int]


@context.register_singleton()
class PixivBindingRepo:

    async def get(self, platform: str, user_id: str) -> Optional[PixivBinding]:
        async with use_pixivbot_session() as session:
            stmt = (select(PixivBindingOrm)
                    .where(PixivBindingOrm.platform == platform,
                           PixivBindingOrm.user_id == user_id)
                    .limit(1))
            result = (await session.execute(stmt)).scalar_one_or_none()
            if result is not None:
                return PixivBinding(platform=result.platform,
                                    user_id=result.user_id,
                                    pixiv_user_id=result.pixiv_user_id)
            else:
                return None

    async def update(self, binding: PixivBinding):
        async with use_pixivbot_session() as session:
            stmt = (insert(PixivBindingOrm)
                    .values(platform=binding.platform,
                            user_id=binding.user_id,
                            pixiv_user_id=binding.pixiv_user_id)
                    .on_conflict_do_update(index_elements=[PixivBindingOrm.platform, PixivBindingOrm.user_id],
                                           set_={
                                               PixivBindingOrm.pixiv_user_id: binding.pixiv_user_id
                                           }))
            await session.execute(stmt)
            await session.commit()

    async def remove(self, platform: str, user_id: str) -> bool:
        async with use_pixivbot_session() as session:
            stmt = (delete(PixivBindingOrm)
                    .where(PixivBindingOrm.platform == platform,
                           PixivBindingOrm.user_id == user_id))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount == 1


__all__ = ("PixivBindingRepo",)

import typing

from .mongo_conn import db
from .pkg_context import context


@context.export_singleton()
class PixivBindings:
    async def bind(self, qq_id: int, pixiv_user_id: int) -> None:
        await db().pixiv_binding.update_one({"qq_id": qq_id},
                                            {"$set": {
                                                "pixiv_user_id": pixiv_user_id
                                            }},
                                            upsert=True)

    async def unbind(self, qq_id: int) -> None:
        await db().pixiv_binding.delete_one({"qq_id": qq_id})

    async def get_binding(self, qq_id: int) -> typing.Optional[int]:
        result = await db().pixiv_binding.find_one({"qq_id": qq_id})
        if result is None:
            return None
        else:
            return result["pixiv_user_id"]


__all__ = ("PixivBindings", )

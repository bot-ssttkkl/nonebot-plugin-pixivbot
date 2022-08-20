from typing import TypeVar, Optional

from nonebot_plugin_pixivbot.data.pixiv_binding_repo import PixivBindingRepo
from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model.pixiv_binding import PixivBinding

UID = TypeVar("UID")


@context.inject
@context.register_singleton()
class PixivAccountBinder:
    repo: PixivBindingRepo

    async def bind(self, adapter: str, user_id: UID, pixiv_user_id: int):
        binding = PixivBinding(adapter=adapter, user_id=user_id, pixiv_user_id=pixiv_user_id)
        await self.repo.update(binding)

    async def unbind(self, adapter: str, user_id: UID) -> bool:
        return await self.repo.remove(adapter, user_id)

    async def get_binding(self, adapter: str, user_id: UID) -> Optional[int]:
        binding = await self.repo.get(adapter, user_id)
        if binding:
            return binding.pixiv_user_id
        else:
            return None

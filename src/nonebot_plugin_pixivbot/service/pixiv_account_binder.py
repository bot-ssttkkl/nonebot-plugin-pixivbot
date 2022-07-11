from typing import TypeVar, Generic, Optional

from nonebot_plugin_pixivbot.data import PixivBindingRepo
from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model.pixiv_binding import PixivBinding
from nonebot_plugin_pixivbot.utils.nonebot import get_adapter_name

UID = TypeVar("UID")


@context.register_singleton()
class PixivAccountBinder(Generic[UID]):
    repo = context.require(PixivBindingRepo)

    async def bind(self, user_id: UID, pixiv_user_id: int):
        binding = PixivBinding(adapter=get_adapter_name(), user_id=user_id, pixiv_user_id=pixiv_user_id)
        await self.repo.update(binding)

    async def unbind(self, user_id: UID) -> bool:
        return await self.repo.remove(get_adapter_name(), user_id)

    async def get_binding(self, user_id: UID) -> Optional[int]:
        binding = await self.repo.get(get_adapter_name(), user_id)
        return binding["pixiv_user_id"]

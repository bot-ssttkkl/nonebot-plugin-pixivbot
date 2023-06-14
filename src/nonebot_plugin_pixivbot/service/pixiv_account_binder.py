from typing import Optional

from ..data.pixiv_binding import PixivBindingRepo
from ..global_context import context
from ..model.pixiv_binding import PixivBinding

repo = context.require(PixivBindingRepo)


@context.register_singleton()
class PixivAccountBinder:

    async def bind(self, platform: str, user_id: str, pixiv_user_id: int):
        binding = PixivBinding(platform=platform, user_id=user_id, pixiv_user_id=pixiv_user_id)
        await repo.update(binding)

    async def unbind(self, platform: str, user_id: str) -> bool:
        return await repo.remove(platform, user_id)

    async def get_binding(self, platform: str, user_id: str) -> Optional[int]:
        binding = await repo.get(platform, user_id)
        if binding:
            return binding.pixiv_user_id
        else:
            return None

from typing import Optional, Protocol

from nonebot_plugin_pixivbot.model import PixivBinding, T_UID


class PixivBindingRepo(Protocol):
    async def get(self, adapter: str, user_id: T_UID) -> Optional[PixivBinding]:
        ...

    async def update(self, binding: PixivBinding):
        ...

    async def remove(self, adapter: str, user_id: T_UID) -> bool:
        ...

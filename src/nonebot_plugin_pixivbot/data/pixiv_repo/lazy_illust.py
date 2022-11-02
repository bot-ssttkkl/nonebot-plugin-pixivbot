from __future__ import annotations

from typing import Optional

from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.utils.lazy_delegation import LazyDelegation

__all__ = ("LazyIllust",)


def _get_src():
    from .base import PixivRepo
    from nonebot_plugin_pixivbot import context
    return context.require(PixivRepo)


class LazyIllust:
    src = LazyDelegation(_get_src)

    def __init__(self, id: int, content: Optional[Illust] = None) -> None:
        self.id = id
        self.content = content

    async def get(self) -> Illust:
        if self.content is None:
            async for x in self.src.illust_detail(self.id):
                self.content = x
                break
        return self.content

    @property
    def loaded(self):
        return self.content is not None

    def __getattr__(self, attr):
        if self.content is None:
            return None
        else:
            return self.content.__getattribute__(attr)

from typing import Optional, Protocol, Collection

from nonebot_plugin_pixivbot.model import Tag, Illust


class LocalTagRepo(Protocol):
    async def find_by_name(self, name: str) -> Optional[Tag]:
        ...

    async def find_by_translated_name(self, translated_name: str) -> Optional[Tag]:
        ...

    async def update_one(self, tag: Tag):
        ...

    async def update_many(self, tags: Collection[Tag]):
        ...

    async def update_from_illusts(self, illusts: Collection[Illust]):
        ...

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, TypeVar, Any, Mapping

from frozendict import frozendict
from pydantic import BaseModel

from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.data.utils.shared_agen import SharedAsyncGeneratorManager
from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .pkg_context import context

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class WatchmanSharedAgenIdentifier(BaseModel):
    type: str
    args: frozendict[str, Any]

    def __init__(self, type: str, args: Mapping[str, Any]):
        if not isinstance(args, frozendict):
            args = frozendict(args)
        super().__init__(type=type, args=args)

    class Config:
        frozen = True


@context.inject
@context.register_singleton()
class WatchmanSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[WatchmanSharedAgenIdentifier, Illust]):
    log_tag = "watchman_shared_agen"

    pixiv: PixivRepo

    async def agen_factory(self, identifier: WatchmanSharedAgenIdentifier,
                           cache_strategy: CacheStrategy,  # 这里的cache_strategy和PixivRepo没关系
                           *args, **kwargs) -> AsyncGenerator[Illust, None]:
        if identifier.type == "user_illusts":
            self.set_expires_time(identifier, datetime.now(timezone.utc) + timedelta(seconds=30))  # 保证每分钟的所有task都能共享
            async for x in self.pixiv.user_illusts(cache_strategy=CacheStrategy.FORCE_EXPIRATION, **identifier.args):
                yield await x.get()
        else:
            raise ValueError(f"invalid type: {identifier.type}")

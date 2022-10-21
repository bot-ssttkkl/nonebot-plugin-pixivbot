from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, TypeVar, Any

from frozendict import frozendict
from pydantic import BaseModel

from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.data.pixiv_repo.enums import CacheStrategy
from nonebot_plugin_pixivbot.data.pixiv_repo.remote_repo import RemotePixivRepo
from nonebot_plugin_pixivbot.model import Illust, WatchType
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from nonebot_plugin_pixivbot.utils.shared_agen import SharedAsyncGeneratorManager
from .pkg_context import context
from .user_following_illusts import user_following_illusts

UID = TypeVar("UID")
GID = TypeVar("GID")

PD = PostDestination[UID, GID]


class WatchmanSharedAgenIdentifier(BaseModel):
    type: WatchType
    kwargs: frozendict[str, Any]

    def __init__(self, type: WatchType, **kwargs):
        super().__init__(type=type, kwargs=frozendict(kwargs))

    def __str__(self):
        return f"({self.type.name} {', '.join(map(lambda k: f'{k}={self.kwargs[k]}', {**self.kwargs}))})"

    class Config:
        frozen = True


@context.inject
@context.register_singleton()
class WatchmanSharedAsyncGeneratorManager(SharedAsyncGeneratorManager[WatchmanSharedAgenIdentifier, Illust]):
    log_tag = "watchman_shared_agen"

    pixiv: PixivRepo
    remote_pixiv: RemotePixivRepo

    async def agen(self, identifier: WatchmanSharedAgenIdentifier, cache_strategy: CacheStrategy, **kwargs) -> AsyncGenerator[Illust, None]:
        self.set_expires_time(identifier, datetime.now(timezone.utc) + timedelta(seconds=30))  # 保证每分钟的所有task都能共享
        if identifier.type == WatchType.user_illusts:
            async for x in self.pixiv.user_illusts(cache_strategy=CacheStrategy.FORCE_EXPIRATION, **identifier.kwargs):
                yield await x.get()
        elif identifier.type == WatchType.following_illusts:
            async for x in user_following_illusts(identifier.kwargs["user_id"]):
                yield x
        else:
            raise ValueError(f"invalid type: {identifier.type}")

from typing import Protocol, TypeVar, AsyncIterable, Optional, Collection

from nonebot_plugin_pixivbot.model import PostIdentifier, T_UID, T_GID

T = TypeVar("T")


class IntervalTaskRepo(Protocol[T]):
    def get_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> AsyncIterable[T]:
        ...

    def get_by_adapter(self, adapter: str) -> AsyncIterable[T]:
        ...

    async def get_by_code(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[T]:
        ...

    async def insert(self, item: T) -> bool:
        ...

    async def delete_one(self, subscriber: PostIdentifier[T_UID, T_GID], code: str) -> Optional[T]:
        ...

    async def delete_many_by_subscriber(self, subscriber: PostIdentifier[T_UID, T_GID]) -> Collection[T]:
        ...


def process_subscriber(subscriber: PostIdentifier[T_UID, T_GID]) -> PostIdentifier[T_UID, T_GID]:
    if subscriber.group_id:
        return PostIdentifier(subscriber.adapter, None, subscriber.group_id)
    elif subscriber.user_id:
        return PostIdentifier(subscriber.adapter, subscriber.user_id, None)
    else:
        raise ValueError("at least one of user_id and group_id should be not None")

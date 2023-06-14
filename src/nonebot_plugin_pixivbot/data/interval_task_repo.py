from typing import Protocol, TypeVar, AsyncIterable, Optional, Collection

from nonebot_plugin_session import Session, SessionLevel

T = TypeVar("T")


class IntervalTaskRepo(Protocol[T]):
    def get_by_session(self, session: Session) -> AsyncIterable[T]:
        ...

    def get_by_bot(self, bot_id: str) -> AsyncIterable[T]:
        ...

    async def get_by_code(self, session: Session,
                          code: str) -> Optional[T]:
        ...

    async def insert(self, item: T) -> bool:
        ...

    async def delete_one(self, session: Session, code: str) -> Optional[T]:
        ...

    async def delete_many_by_session(self, session: Session) -> Collection[T]:
        ...


def process_subscriber(subscriber: Session) -> Session:
    if subscriber.level != SessionLevel.LEVEL1:
        return subscriber.copy(update=dict(id1="0"))
    else:
        return subscriber

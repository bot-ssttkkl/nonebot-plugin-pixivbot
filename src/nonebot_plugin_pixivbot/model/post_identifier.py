from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.postman import PostDestination, PostDestinationFactoryManager

UID = TypeVar("UID")
GID = TypeVar("GID")


@dataclass(frozen=True)
class PostIdentifier(Generic[UID, GID]):
    adapter: str
    user_id: Optional[UID]
    group_id: Optional[GID]

    def __post_init__(self):
        if not self.user_id and not self.group_id:
            raise ValueError("at least one of user_id and group_id should be not None")

    @staticmethod
    def from_post_dest(post_dest: PostDestination):
        return PostIdentifier(post_dest.adapter, post_dest.user_id, post_dest.group_id)

    def to_post_dest(self, adapter: str):
        factory = context.require(PostDestinationFactoryManager)[adapter]
        post_dest = factory.build(self.user_id, self.group_id)
        return post_dest

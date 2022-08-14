from typing import TypeVar

from nonebot_plugin_pixivbot.model import PostIdentifier

UID = TypeVar("UID")
GID = TypeVar("GID")

ID = PostIdentifier[UID, GID]


def process_subscriber(subscriber: ID) -> PostIdentifier[UID, GID]:
    if subscriber.group_id:
        return PostIdentifier(subscriber.adapter, None, subscriber.group_id)
    elif subscriber.user_id:
        return PostIdentifier(subscriber.adapter, subscriber.user_id, None)
    else:
        raise ValueError("at least one of user_id and group_id should be not None")

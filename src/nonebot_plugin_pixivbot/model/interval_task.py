from typing import Generic

from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import T_UID, T_GID, PostIdentifier, UserIdentifier


class IntervalTask(GenericModel, Generic[T_UID, T_GID]):
    code: str = ""
    bot: UserIdentifier[str]  # 因为Bot.self_id恒为str
    subscriber: PostIdentifier[T_UID, T_GID]
